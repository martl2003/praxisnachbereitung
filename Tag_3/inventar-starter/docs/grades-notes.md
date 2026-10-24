# Notizen zum Referenzprojekt `grades-starter` (Aufgabe B)

## 1. Wie ist das Projekt strukturiert?

Das Projekt trennt Infrastruktur, Datenbank-Initialisierung und Backend-Anwendung sauber voneinander:

```text
grades-starter/
├── docker-compose.yml              # Services: db (Postgres 16), mqtt (Mosquitto 2), api (FastAPI)
├── Dockerfile                      # Python 3.12 Container mit Uvicorn (--reload)
├── requirements.txt                # FastAPI, Uvicorn, Jinja2, psycopg[binary], Pydantic, paho-mqtt, python-multipart
├── db/init/
│   └── 001_schema.sql              # Tabellen (student, module, grade), Constraints & Seed-Daten
├── mqtt/
│   └── mosquitto.conf              # Broker-Konfiguration (Port 1883 TCP, 9001 WebSockets)
└── backend/app/
    ├── db.py                       # DB-Verbindungsaufbau via psycopg + dict_row + autocommit=True
    ├── models.py                   # Pydantic-Modelle für Request-Validierung & Entitäten
    ├── mqtt_integration.py         # Hintergrund-Thread für eingehende MQTT-Nachrichten (grades/new)
    ├── main.py                     # FastAPI-Routen (HTML-Seiten, Form-POSTs, HTMX-Teilupdates, CSV-Export, /health)
    └── templates/
        ├── index.html              # Startseite mit Links und MQTT-Beispiel
        ├── students/
        │   ├── index.html          # Liste + Formular zum Anlegen/Löschen von Studierenden
        │   └── edit.html           # Formular zum Bearbeiten eines Studierenden
        └── grades/
            ├── index.html          # Notenübersicht + HTMX-Formular
            └── _list.html          # Teil-Template (Partial) für die Notentabelle
```

---

## 2. Gezielte Analyse der Referenzstellen (Aufgabe B.2)

### DB-Init: `db/init/001_schema.sql`
- **Welche Tabellen gibt es?**
  1. `student` (`student_id`, `matrikel`, `vorname`, `nachname`, `programme`, `semester`)
  2. `module` (`module_id`, `name`)
  3. `grade` (`grade_id`, `student_id`, `module_id`, `grade_value`, `graded_at`)
- **Wo stehen Constraints (`UNIQUE`, `CHECK`, `FK`)?**
  - **Primary Keys**: `serial primary key` auf `student_id`, `module_id`, `grade_id`.
  - **UNIQUE-Constraints**:
    - `student.matrikel text not null unique` (Matrikelnummer eindeutig)
    - `module.name text not null unique` (Modulname eindeutig)
  - **CHECK-Constraints**:
    - `semester int not null check (semester between 1 and 12)` in der Tabelle `student`.
  - **Foreign Keys (FK)**:
    - `grade.student_id int not null references student(student_id) on delete cascade`
    - `grade.module_id int not null references module(module_id) on delete cascade`
  - **Idempotente Seed-Daten**:
    - Werden direkt am Ende des Skripts per `INSERT INTO ... ON CONFLICT (...) DO NOTHING` eingefügt.

### DB-Zugriff: `backend/app/db.py`
- **Wie wird `get_conn()` verwendet?**
  - `get_conn()` öffnet eine `psycopg.connect(...)`-Verbindung mit `row_factory=dict_row` (Ergebniszeilen als Python-Dictionaries statt Tupel) und `autocommit=True`.
  - In den Endpunkten (`main.py`) wird `get_conn()` immer als **Context-Manager** zusammen mit `conn.cursor()` genutzt:
    ```python
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT ... WHERE student_id = %s", (student_id,))
        row = cur.fetchone()
    ```
  - Parameter werden sicher über Platzhalter (`%s`) übergeben (Schutz vor SQL-Injection).

### API: Routen für Students / Grades (`backend/app/main.py`)
- **Wo werden Routen definiert?**
  - Direkt in `backend/app/main.py` an der zentralen `FastAPI`-Instanz `app`:
    - Studierende: `GET /students`, `POST /students`, `GET /students/{student_id}/edit`, `POST /students/{student_id}/edit`, `POST /students/{student_id}/delete`
    - Module: `POST /modules`
    - Noten: `GET /grades`, `GET /grades/htmx`, `POST /grades/htmx`, `GET /grades.csv`
    - Infrastruktur: `GET /health`, `GET /`

### Models: `backend/app/models.py`
- **Wie werden Models aufgebaut?**
  - Sie erben von `pydantic.BaseModel` und trennen zwischen:
    - **Eingabe-Modellen (Create/Update)** ohne generierte DB-Felder (`StudentCreate`, `StudentUpdate`, `ModuleCreate`, `GradeCreate`)
    - **Lese-/Entitäts-Modellen** inklusive Primärschlüssel und Zeitstempel (`Student`, `Module`, `Grade` mit `grade_id: int` und `graded_at: datetime`).

### UI: Templates unter `backend/app/templates/…`
- **Wie sind die Templates aufgebaut?**
  - Eigenständige Seiten (`index.html`, `students/index.html`, `students/edit.html`, `grades/index.html`) enthalten das HTML-Grundgerüst und Inline-CSS.
  - Teil-Templates wie `grades/_list.html` enthalten nur das `<table>`-Fragment und werden sowohl initial per `{% include "grades/_list.html" %}` eingebunden als auch bei HTMX-Requests einzeln gerendert.

---

## 3. Beantwortung der Leitfragen (Aufgabe B.3)

### Wie werden Formulare verarbeitet?
- HTML-Formulare senden `application/x-www-form-urlencoded` (benötigt das Paket `python-multipart`).
- FastAPI nimmt die Felder über `Form(...)` entgegen (z. B. `matrikel: str = Form(...)`) und übergibt sie zur Validierung an ein Pydantic-Modell (`data = StudentCreate(...)`).
- Nach dem DB-Schreibzugriff folgt bei klassischen Formularen ein **Post/Redirect/Get-Flow** mittels `RedirectResponse(target, status_code=303)`, damit ein Browser-Reload kein doppeltes Absenden auslöst.

### Wie werden Templates eingebunden?
- Über `Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))`.
- Routen mit `response_class=HTMLResponse` rufen `templates.TemplateResponse("...", {"request": request, ...})` auf und übergeben die geladenen DB-Dictionaries an Jinja2.

### Wie sehen einfache CRUD-Flows aus?
1. **Read (Auflisten)**: `GET /students` lädt alle Datensätze per `cur.fetchall()` und rendert die Tabelle in `students/index.html`.
2. **Create (Anlegen)**: Formular sendet `POST /students` -> Validierung über `StudentCreate` -> `INSERT INTO student ...` -> `RedirectResponse("/students", status_code=303)`.
3. **Update (Bearbeiten)**: `GET /students/{id}/edit` lädt den Datensatz in ein vorausgefülltes Formular -> `POST /students/{id}/edit` führt `UPDATE student SET ... WHERE student_id = %s` aus -> Redirect auf `/students`.
4. **Delete (Löschen)**: Kleines Inline-Formular in der Tabellenzeile sendet `POST /students/{id}/delete` -> `DELETE FROM student WHERE student_id = %s` -> Redirect auf `/students`.
5. **HTMX-Teil-Update + MQTT**: Bei `POST /grades/htmx` wird die Note per `INSERT ... RETURNING` gespeichert, direkt ein MQTT-Event (`publish_grade_created`) gesendet und nur das Tabellen-Partial `grades/_list.html` an HTMX (`hx-target="#grade-list"`) zurückgegeben.
