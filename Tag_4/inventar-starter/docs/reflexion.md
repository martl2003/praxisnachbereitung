# Reflexion: Unsere FastAPI-Inventar-App – Stärken & Schwächen

## Stärken

- **Einfach & nachvollziehbar:** Ein Einstiegspunkt (`backend/app/main.py`), SQL steht explizit im Code, keine ORM-„Magie“.
- **Domänenregeln doppelt abgesichert:** IR-01 bis IR-03 stehen als Constraints in der DB (letzte Verteidigungslinie) und werden in der API in verständliche Statuscodes übersetzt (409/422 statt 500).
- **Typisierte Schnittstellen:** Pydantic-Modelle (`DeviceCreate`, `AssignmentOut`, …) validieren Eingaben und erzeugen automatisch die Doku unter `/docs`.
- **Mehrere Kanäle aus einer App:** JSON-API, HTML-UI (Jinja + htmx), MQTT-Events und seit Tag 4 CSV/XLSX-Export für Excel.
- **Prod-nahes Setup:** Alles läuft reproduzierbar in Docker, die Konfiguration kommt aus `.env`.
- **Schema jetzt versioniert:** Mit Alembic ist nachvollziehbar, welcher Schemastand auf welcher DB läuft (`alembic current`, `alembic history`), inkl. Rückweg (`downgrade`).
- **Sicher gegen gleichzeitige Ausleihen:** Die API prüft IR-02 vorab, aber erst der partielle Unique-Index in der DB macht es wasserdicht. Klicken zwei Personen gleichzeitig auf „Ausgeben“, gewinnt genau eine; die andere bekommt 409.
- **Historie bleibt erhalten:** `ON DELETE RESTRICT` verhindert, dass ein Gerät oder eine Person mit Ausleihen gelöscht wird. Die Ausleih-Historie kann nicht versehentlich verloren gehen.
- **Robust gegenüber MQTT-Ausfall:** Ist der Broker nicht erreichbar, wird der Fehler abgefangen. Die Ausleihe wird trotzdem gespeichert, nur das Event fehlt.
- **Gute Betreibbarkeit:** `/health` prüft DB *und* MQTT getrennt (`ok` / `degraded`); Compose startet die API erst, wenn die DB „healthy“ ist.
- **Eine Schnittstelle für UI und Tools:** Dieselben Endpunkte nehmen JSON (Swagger, curl) und HTML-Formulare (UI) an. Die Domänenregeln gelten so automatisch für beide Wege.
- **Kein Frontend-Build nötig:** Jinja + htmx liefern Teil-Updates ohne React/Node-Toolchain. Ein Python-Container reicht.
- **Offene Datenschnittstelle statt Dateischieberei:** Excel holt die Daten per URL (`/assignments.csv`) immer aktuell aus der DB, statt veraltete Kopien per Mail zu verteilen (Problem von Tag 1).
- **Nachvollziehbare Tests:** `crud_test.http` dokumentiert die wichtigsten Fälle (inkl. 409/422) und ist für alle im Team wiederholbar.

## Schwächen / Grenzen

- **Alles in einer Datei:** `main.py` hat über 600 Zeilen. Routing, SQL, Fehlerbehandlung und HTML-Rendering sind vermischt.
- **Doppelte Logik:** Jeder Endpunkt bedient JSON *und* HTML (`wants_html`). Dadurch steht die Fehlerbehandlung mehrfach im Code. SQL-Abfragen sind ähnlich doppelt (`fetch_devices` / `fetch_device_by_id`).
- **Sync-DB in `async def`:** psycopg wird synchron aufgerufen und blockiert dabei den Event-Loop. Bei Last wäre `def` (Threadpool) oder ein async-Treiber besser.
- **Code und Schema sind gekoppelt, aber nicht abgesichert:** Nach `alembic downgrade -1` liefert `/assignments.csv` einen 500er, weil der Code `purchase_price` erwartet. Es gibt keinen Check, ob die DB auf `head` steht.
- **Migrationen laufen manuell:** `alembic upgrade head` muss man selbst ausführen. Vergisst man es, startet die App ohne Tabellen.
- **Keine automatisierten Tests:** Getestet wird manuell über `/docs` und `crud_test.http`; kein pytest, keine CI.
- **Keine Sicherheit:** Keine Authentifizierung/Rollen; MQTT läuft anonym (`allow_anonymous true`).
- **Kein Admin-Backend:** Stammdaten (Personen, Abteilungen, Standorte, Gerätetypen) lassen sich nur per SQL/Migration pflegen.
- **Zeitzonen uneinheitlich:** `parse_timestamp` behandelt Zeitangaben ohne Zeitzone als UTC, der Export rechnet aber in `Europe/Berlin`. Wer „10:00“ ohne Zone eingibt, sieht im Excel „11:00“ bzw. „12:00“.
- **Keine Paginierung:** `GET /devices`, `GET /assignments` und der Export liefern immer *alle* Zeilen und bauen die Datei komplett im Speicher. Bei vielen Tausend Ausleihen wird das langsam.
- **Neue Verbindung pro Request:** Jede Anfrage öffnet eine eigene DB-Verbindung (kein Connection-Pool), jedes MQTT-Event eine eigene Broker-Verbindung.
- **Logging nur per `print`:** Fehlgeschlagene MQTT-Events landen nur als `print` im Container-Log; es gibt kein strukturiertes Logging und kein Monitoring.
- **Zugangsdaten im Repository:** `.env` mit DB-Passwort ist committet, und Postgres ist auf Port 5432 nach außen offen. Für die Übung okay, produktiv ein Sicherheitsrisiko.
- **Dev-Modus im Container:** Uvicorn läuft mit `--reload` und der Code ist als Volume gemountet. Praktisch beim Entwickeln, aber kein Produktions-Setup.
- **Testdaten in der Migration:** Die Seed-Daten stecken in `20261025_01_initial`. Auf einer echten Produktions-DB würden damit auch Testpersonen und -geräte angelegt.
- **Export nicht exakt reproduzierbar:** `duration_days` wird für aktive Ausleihen mit `now()` berechnet. Derselbe Export liefert zu einem späteren Zeitpunkt andere Werte.
- **Abhängigkeit vom Internet:** htmx wird per CDN (`unpkg.com`) geladen; ohne Internet fehlen die Teil-Updates in der UI.

## Vergleich zu „großen“ Frameworks (Rails, Django)

| Thema | FastAPI (unsere App) | Rails / Django |
|---|---|---|
| Projektstruktur | selbst definieren | Konvention vorgegeben |
| Scaffolding (CRUD generieren) | von Hand | `rails g scaffold` / Admin |
| Admin-Oberfläche | selbst bauen | eingebaut |
| Migrationen | Alembic als Zusatztool | integriert |
| Flexibilität / Leichtgewicht | hoch | geringer, dafür „all inclusive“ |

## Nächste Schritte (wenn das ein echtes Projekt wäre)

1. `main.py` aufteilen: `routers/`, `services/` (Regeln), `repositories/` (SQL), `schemas/` (Pydantic).
2. JSON-API und HTML-UI trennen (UI ruft dieselben Services auf, statt jeden Endpunkt doppelt zu bedienen).
3. Migrationen beim Container-Start automatisch ausführen (`alembic upgrade head && uvicorn …`).
4. pytest-Tests für IR-01 bis IR-03 und eine CI-Pipeline (GitHub Actions) mit ruff.
5. Login/Rollen sowie MQTT mit Benutzer/ACL.

**Fazit:** FastAPI ist kein Rails-Ersatz, sondern ein leichtgewichtiger Baukasten. Struktur, Konventionen und Zusatztools (Alembic, Tests, Auth) muss sich das Team bewusst dazuholen.
