# Grades Starter

Referenzprojekt für **Tag 3**: ausgehend vom technischen Stack aus Tag 2 wird hier eine fachliche Mini-App für **Studierende / Module / Grade** gezeigt.

Enthalten sind:

- FastAPI
- PostgreSQL
- MQTT (Eclipse Mosquitto)
- Jinja + htmx für eine einfache serverseitige UI
- CSV-Export `grades.csv`

Wichtig:

- Dieses Projekt dient als **Blaupause**.
- Für die eigentliche Übung entwickelt ihr im `inventar-starter`.

## Schnellstart

```bash
docker compose up -d --build
```

Danach prüfen:

```bash
curl http://localhost:8000/health    # {"status":"ok","db":"ok","mqtt":"ok"}
open http://localhost:8000/          # Startseite
open http://localhost:8000/health    # {"status":"ok","db":"ok","mqtt":"ok"}
open http://localhost:8000/grades    # Notenübersicht
open http://localhost:8000/students  # Studierende verwalten
open http://localhost:8000/docs      # OpenAPI
```

Services:

- API: http://localhost:8000
- Postgres: localhost:5432
- MQTT: localhost:1883 (TCP), localhost:9001 (WebSockets)

## Wichtige Endpunkte

- `GET /` – Startseite mit Überblick
- `GET /students` – Studierende verwalten
- `GET /grades` – Notenübersicht und Formular
- `POST /students` – neuen Studierenden anlegen
- `POST /modules` – neues Modul anlegen
- `POST /grades/htmx` – neue Note anlegen
- `GET /grades.csv` – CSV-Export aller Noten
- `GET /health` – Health-Check für DB und MQTT
- `GET /docs` – OpenAPI-Dokumentation

## Datenmodell

Tabellen:

- `student (student_id, matrikel, vorname, nachname, programme, semester)`
- `module (module_id, name)`
- `grade (grade_id, student_id, module_id, grade_value, graded_at)`

Beim ersten Start werden in [db/init/001_schema.sql](db/init/001_schema.sql) einige Seed-Daten angelegt.

## MQTT

Die API abonniert beim Start das Topic:

- `grades/new`

Beim Anlegen einer Note über das Formular unter `/grades` publiziert die App zusätzlich auf:

- `grades/created`

Erwartetes Payload-Format:

```json
{
  "student_id": 1,
  "module_id": 2,
  "grade_value": "1,7"
}
```

Beispiel-Publish:

```bash
mosquitto_pub -h localhost -p 1883 -t "grades/new" -m '{"student_id":1,"module_id":2,"grade_value":"1,0"}'
```

Nach erfolgreichem Publish sollte die neue Note unter `/grades` und im CSV-Export `/grades.csv` sichtbar sein.

Wenn ihr eine Note über die Oberfläche anlegt, könnt ihr das neue Event z. B. so beobachten:

```bash
mosquitto_sub -h localhost -p 1883 -t "grades/created" -v
```

## Entwicklungsumgebung

Analog zu Tag 2 sind enthalten:

- `.devcontainer/` für VS Code Dev Container
- `.vscode/tasks.json` für `compose up`, `compose down`, `logs api`, `logs mqtt`
- `.env` für optionale lokale Overrides
