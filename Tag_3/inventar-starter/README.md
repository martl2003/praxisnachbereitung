# Inventar-App (Tag 3)

Vollständige Inventarverwaltung auf Basis von **FastAPI**, **PostgreSQL**, **Jinja2 + HTMX** und **Eclipse Mosquitto (MQTT)**.

- Referenz-Notizen zu Aufgabe B: [docs/grades-notes.md](docs/grades-notes.md)
- HTTP-Requests zum schnellen API-Testen (Aufgabe E.5): [crud_test.http](crud_test.http)
- Datenbank-Schema & Seed-Daten: [db/init/010_inventory_schema.sql](db/init/010_inventory_schema.sql)

---

## Schnellstart

```bash
docker compose up -d --build
```

Wichtige URLs:

- Startseite: `http://localhost:8000/`
- Inventar-UI: `http://localhost:8000/inventory`
- Health-Check: `http://localhost:8000/health`
- OpenAPI / Swagger: `http://localhost:8000/docs`

---

## H) Prüfliste & Präsentation

### Prüfliste am Ende
- [x] `inventar-starter` wurde als Arbeitsbasis übernommen
- [x] Ein sauberer Basisstand wurde zunächst auf `main` committed
- [x] Die eigentliche Arbeit erfolgte in Feature-Branches (und wurde nach `main` gemerged)
- [x] Init-SQL für Inventar ([db/init/010_inventory_schema.sql](db/init/010_inventory_schema.sql)) ist angelegt und erzeugt alle 6 Tabellen inkl. Seed-Daten
- [x] REST-Endpunkte für Devices & Assignments funktionieren inkl. Domänenregeln (`IR-01`, `IR-02`, `IR-03`)
- [x] Einfache UI-Seite unter `/inventory` (inkl. HTMX-Teilupdates & CSS-Animation) ist vorhanden
- [x] MQTT wird für Inventar-Ereignisse (`inventory/assignments/issued` & `inventory/assignments/returned`) genutzt
- [x] Branch-Wechsel, Schema, API und UI-Flow sind unten mit Code-Ausschnitten dokumentiert

---

## Ablauf & Code-Stellen für die Präsentation

### 1. Laufende App & Endpunkte zeigen
- Health-Check: `http://localhost:8000/health` -> `{"status":"ok","db":"ok","mqtt":"ok"}`
- API-Dokumentation: `http://localhost:8000/docs` oder direkt über [crud_test.http](crud_test.http)
- Inventar-Oberfläche: `http://localhost:8000/inventory`

### 2. Live-Flow in der UI (`/inventory`) + MQTT vorführen
In einem Terminal den MQTT-Subscriber starten:

```bash
docker compose exec mqtt mosquitto_sub -h localhost -t 'inventory/assignments/#' -v
```

Optional für den **MQTT-Chat zwischen zwei Terminals**:
```bash
# Terminal 1 (Subscriber)
docker compose exec mqtt mosquitto_sub -h localhost -t 'inventory/chat' -v

# Terminal 2 (Publisher)
docker compose exec mqtt mosquitto_pub -h localhost -t 'inventory/chat' -m 'Hallo aus Terminal 2!'
```

Danach auf `http://localhost:8000/inventory`:
1. **Device anlegen**: Seriennummer (z. B. `SN-LAP-099`), Typ und Standort wählen -> *Gerät anlegen*.
2. **Device ausgeben**: Person + das neue freie Gerät wählen -> *Ausgeben* (MQTT-Event auf `inventory/assignments/issued` erscheint sofort im Terminal).
3. **Device zurückgeben**: In *Aktive Ausleihen* auf *Zurückgeben* klicken (MQTT-Event auf `inventory/assignments/returned` erscheint im Terminal, Status wechselt zurück auf `frei`).

---

### 3. Code-Erklärungen (Aufgabe H.4)

#### Stelle 1: SQL-Schema & Constraints ([db/init/010_inventory_schema.sql](db/init/010_inventory_schema.sql))
Alle drei Domänenregeln (`IR-01`, `IR-02`, `IR-03`) sind direkt in PostgreSQL abgesichert:

```sql
CREATE TABLE device (
    device_id      integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    serial_number  varchar(100) NOT NULL,
    device_type_id integer      NOT NULL,
    location_id    integer      NOT NULL,
    note           text         NULL,

    -- IR-01: serial_number ist eindeutig
    CONSTRAINT uq_device_serial_number UNIQUE (serial_number),
    CONSTRAINT fk_device_type
        FOREIGN KEY (device_type_id) REFERENCES device_type (device_type_id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_device_location
        FOREIGN KEY (location_id) REFERENCES location (location_id)
        ON DELETE RESTRICT
);

CREATE TABLE assignment (
    assignment_id integer     GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    device_id     integer     NOT NULL,
    person_id     integer     NOT NULL,
    issued_at     timestamptz NOT NULL DEFAULT now(),
    returned_at   timestamptz NULL,

    -- IR-03: returned_at darf nicht vor issued_at liegen
    CONSTRAINT chk_assignment_dates
        CHECK (returned_at IS NULL OR returned_at >= issued_at),
    CONSTRAINT fk_assignment_device
        FOREIGN KEY (device_id) REFERENCES device (device_id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_assignment_person
        FOREIGN KEY (person_id) REFERENCES person (person_id)
        ON DELETE RESTRICT
);

-- IR-02: Ein Device darf maximal eine aktive Ausleihe haben (Partial Unique Index)
CREATE UNIQUE INDEX uq_assignment_active_device
    ON assignment (device_id)
    WHERE returned_at IS NULL;
```

---

#### Stelle 2: API-Endpunkt & Domänenregel `IR-02` + MQTT beim Ausgeben ([backend/app/main.py](backend/app/main.py))
Beim Anlegen einer Ausleihe (`POST /assignments`) wird geprüft, ob bereits eine offene Ausleihe (`returned_at IS NULL`) für das Gerät existiert. Im Fehlerfall wird `409 Conflict` geliefert, bei Erfolg wird das MQTT-Event publiziert:

```python
@app.post("/assignments", response_model=AssignmentOut, status_code=201)
async def create_assignment(request: Request):
    data: AssignmentCreate = await parse_payload(request, AssignmentCreate)
    issued_dt = parse_timestamp(data.issued_at, "issued_at")

    try:
        with get_conn() as conn, conn.cursor() as cur:
            # IR-02: Prüfen, ob Device bereits aktiv ausgeliehen ist
            cur.execute(
                "SELECT assignment_id FROM assignment WHERE device_id = %s AND returned_at IS NULL",
                (data.device_id,),
            )
            if cur.fetchone():
                raise HTTPException(
                    status_code=409,
                    detail=f"IR-02 verletzt: Device {data.device_id} hat bereits eine aktive Ausleihe.",
                )

            cur.execute(
                """
                INSERT INTO assignment (device_id, person_id, issued_at)
                VALUES (%s, %s, COALESCE(%s, now()))
                RETURNING assignment_id
                """,
                (data.device_id, data.person_id, issued_dt),
            )
            created = cur.fetchone()
            assignment = fetch_assignment_by_id(cur, created["assignment_id"])
    except psycopg.errors.UniqueViolation as exc:
        raise HTTPException(
            status_code=409,
            detail=f"IR-02 verletzt: Device {data.device_id} hat bereits eine aktive Ausleihe.",
        ) from exc

    # MQTT-Event auf 'inventory/assignments/issued' senden
    publish_assignment_event(MQTT_ISSUED_TOPIC, "issued", assignment)
    return assignment
```

---

#### Stelle 3: Domänenregeln `IR-01` (409 Conflict) & `IR-03` (422 Unprocessable Entity) ([backend/app/main.py](backend/app/main.py))

- **IR-01 (Eindeutige Seriennummer in `POST /devices` & `PUT /devices/{id}`)**:
  ```python
  except psycopg.errors.UniqueViolation as exc:
      detail = f"IR-01 verletzt: Seriennummer '{serial}' existiert bereits."
      raise HTTPException(status_code=409, detail=detail) from exc
  ```

- **IR-03 (`returned_at >= issued_at` in `POST /assignments/{assignment_id}/return`)**:
  ```python
  effective_return = returned_dt or datetime.now(timezone.utc)
  if effective_return < existing["issued_at"]:
      raise HTTPException(
          status_code=422,
          detail="IR-03 verletzt: returned_at darf nicht vor issued_at liegen.",
      )
  ```
