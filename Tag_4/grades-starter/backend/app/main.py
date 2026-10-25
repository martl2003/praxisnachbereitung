from fastapi import FastAPI, Request, Form, Response
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
import os, io, csv, json
import paho.mqtt.client as mqtt

from .db import get_conn
from .models import StudentCreate, StudentUpdate, ModuleCreate, GradeCreate, Grade
from .mqtt_integration import start_mqtt_listener

app = FastAPI(title="Grades Starter", version="0.1.0")
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))
MQTT_HOST = os.getenv("MQTT_HOST", "mqtt")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_CREATED_TOPIC = os.getenv("MQTT_GRADE_CREATED_TOPIC", "grades/created")


def mqtt_client() -> mqtt.Client:
  client = mqtt.Client()
  client.connect(MQTT_HOST, MQTT_PORT, keepalive=30)
  return client


def publish_grade_created(row) -> None:
  payload = {
    "grade_id": row["grade_id"],
    "student_id": row["student_id"],
    "module_id": row["module_id"],
    "grade_value": row["grade_value"],
    "graded_at": row["graded_at"].isoformat(sep=" ", timespec="seconds"),
  }

  try:
    client = mqtt_client()
    client.publish(MQTT_CREATED_TOPIC, json.dumps(payload), qos=0, retain=False)
    client.disconnect()
  except Exception as exc:
    print(f"[MQTT] Publish auf '{MQTT_CREATED_TOPIC}' fehlgeschlagen:", exc)


@app.on_event("startup")
def startup_event():
  start_mqtt_listener()


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
  return templates.TemplateResponse(
    "index.html",
    {"request": request, "title": "Grades Starter"}
  )


@app.get("/students", response_class=HTMLResponse)
def students_page(request: Request):
  with get_conn() as conn, conn.cursor() as cur:
    cur.execute(
      "select student_id, matrikel, vorname, nachname, programme, semester from student order by nachname, vorname"
    )
    students = list(cur.fetchall())

  return templates.TemplateResponse(
    "students/index.html",
    {"request": request, "title": "Studierende", "students": students},
  )


@app.get("/students/{student_id}/edit", response_class=HTMLResponse)
def edit_student_page(request: Request, student_id: int):
  with get_conn() as conn, conn.cursor() as cur:
    cur.execute(
      "select student_id, matrikel, vorname, nachname, programme, semester from student where student_id = %s",
      (student_id,),
    )
    student = cur.fetchone()

  if not student:
    return RedirectResponse("/students", status_code=303)

  return templates.TemplateResponse(
    "students/edit.html",
    {"request": request, "title": "Student bearbeiten", "student": student},
  )


@app.post("/students/{student_id}/edit", response_class=HTMLResponse)
def update_student(
  request: Request,
  student_id: int,
  matrikel: str = Form(...),
  vorname: str = Form(...),
  nachname: str = Form(...),
  programme: str = Form(...),
  semester: int = Form(...),
  return_to: str | None = Form(None),
):
  data = StudentUpdate(
    matrikel=matrikel,
    vorname=vorname,
    nachname=nachname,
    programme=programme,
    semester=semester,
  )
  with get_conn() as conn, conn.cursor() as cur:
    cur.execute(
      """
      update student
      set matrikel = %s,
          vorname = %s,
          nachname = %s,
          programme = %s,
          semester = %s
      where student_id = %s
      """,
      (data.matrikel, data.vorname, data.nachname, data.programme, data.semester, student_id),
    )

  target = return_to or "/students"
  return RedirectResponse(target, status_code=303)


@app.post("/students/{student_id}/delete", response_class=HTMLResponse)
def delete_student(
  request: Request,
  student_id: int,
  return_to: str | None = Form(None),
):
  with get_conn() as conn, conn.cursor() as cur:
    cur.execute("delete from student where student_id = %s", (student_id,))

  target = return_to or "/students"
  return RedirectResponse(target, status_code=303)


@app.post("/students", response_class=HTMLResponse)
def create_student(
  request: Request,
  matrikel: str = Form(...),
  vorname: str = Form(...),
  nachname: str = Form(...),
  programme: str = Form(...),
  semester: int = Form(...),
  return_to: str | None = Form(None),
):
  data = StudentCreate(
    matrikel=matrikel,
    vorname=vorname,
    nachname=nachname,
    programme=programme,
    semester=semester,
  )
  with get_conn() as conn, conn.cursor() as cur:
    cur.execute(
      """
      insert into student (matrikel, vorname, nachname, programme, semester)
      values (%s, %s, %s, %s, %s)
      on conflict (matrikel) do nothing
      """,
      (data.matrikel, data.vorname, data.nachname, data.programme, data.semester),
    )
  if return_to:
    return RedirectResponse(return_to, status_code=303)
  return grades_page(request)


@app.post("/modules", response_class=HTMLResponse)
def create_module(request: Request, name: str = Form(...)):
  data = ModuleCreate(name=name)
  with get_conn() as conn, conn.cursor() as cur:
    cur.execute(
      "insert into module (name) values (%s) on conflict (name) do nothing",
      (data.name,),
    )
  return grades_page(request)


@app.get("/grades", response_class=HTMLResponse)
def grades_page(request: Request, student_id: int | None = None):
  with get_conn() as conn, conn.cursor() as cur:
    cur.execute("select student_id, matrikel, vorname, nachname from student order by nachname, vorname")
    students = list(cur.fetchall())

    cur.execute("select module_id, name from module order by name")
    modules = list(cur.fetchall())

    current_student_id = student_id
    if current_student_id is None and students:
      current_student_id = students[0]["student_id"]

    grades = []
    if current_student_id is not None:
      cur.execute(
        """
        select g.grade_id,
               s.matrikel,
               s.vorname,
               s.nachname,
               s.programme,
               s.semester,
               m.name as module_name,
               g.grade_value,
               g.graded_at
        from grade g
        join student s on s.student_id = g.student_id
        join module m on m.module_id = g.module_id
        where s.student_id = %s
        order by g.graded_at desc
        """,
        (current_student_id,),
      )
      grades = list(cur.fetchall())

  return templates.TemplateResponse(
    "grades/index.html",
    {
      "request": request,
      "title": "Notenübersicht",
      "students": students,
      "modules": modules,
      "grades": grades,
      "current_student_id": current_student_id,
    },
  )


@app.post("/grades/htmx", response_class=HTMLResponse)
def create_grade_htmx(
  request: Request,
  student_id: int = Form(...),
  module_id: int = Form(...),
  grade_value: str = Form(...),
):
  data = GradeCreate(student_id=student_id, module_id=module_id, grade_value=grade_value)
  with get_conn() as conn, conn.cursor() as cur:
    cur.execute(
      """
      insert into grade (student_id, module_id, grade_value)
      values (%s, %s, %s)
      returning grade_id, student_id, module_id, grade_value, graded_at
      """,
      (data.student_id, data.module_id, data.grade_value),
    )
    row = cur.fetchone()
    if row:
      _ = Grade(**row)
      publish_grade_created(row)

    cur.execute(
      """
      select g.grade_id,
             s.matrikel,
             s.vorname,
             s.nachname,
             s.programme,
             s.semester,
             m.name as module_name,
             g.grade_value,
             g.graded_at
      from grade g
      join student s on s.student_id = g.student_id
      join module m on m.module_id = g.module_id
      where s.student_id = %s
      order by g.graded_at desc
      """,
      (data.student_id,),
    )
    grades = list(cur.fetchall())

  return templates.TemplateResponse(
    "grades/_list.html",
    {"request": request, "grades": grades},
  )


@app.get("/grades/htmx", response_class=HTMLResponse)
def grades_htmx(request: Request, student_id: int | None = None):
  with get_conn() as conn, conn.cursor() as cur:
    # Fallback: erster Student, falls keiner gewählt ist
    if student_id is None:
      cur.execute("select student_id from student order by nachname, vorname limit 1")
      row = cur.fetchone()
      if row:
        student_id = row["student_id"]

    grades = []
    if student_id is not None:
      cur.execute(
        """
        select g.grade_id,
               s.matrikel,
               s.vorname,
               s.nachname,
               s.programme,
               s.semester,
               m.name as module_name,
               g.grade_value,
               g.graded_at
        from grade g
        join student s on s.student_id = g.student_id
        join module m on m.module_id = g.module_id
        where s.student_id = %s
        order by g.graded_at desc
        """,
        (student_id,),
      )
      grades = list(cur.fetchall())

  return templates.TemplateResponse(
    "grades/_list.html",
    {"request": request, "grades": grades},
  )


@app.get("/grades.csv")
def grades_csv():
  with get_conn() as conn, conn.cursor() as cur:
    cur.execute(
      """
      select g.grade_id,
             s.matrikel,
             s.vorname,
             s.nachname,
             s.programme,
             s.semester,
             m.name as module_name,
             g.grade_value,
             g.graded_at
      from grade g
      join student s on s.student_id = g.student_id
      join module m on m.module_id = g.module_id
      order by s.matrikel, m.name, g.graded_at
      """,
    )
    rows = list(cur.fetchall())

  buf = io.StringIO()
  fieldnames = [
    "grade_id",
    "matrikel",
    "vorname",
    "nachname",
    "programme",
    "semester",
    "module_name",
    "grade_value",
    "graded_at",
  ]
  writer = csv.DictWriter(buf, fieldnames=fieldnames, delimiter=";", lineterminator="\n")
  writer.writeheader()
  for r in rows:
    writer.writerow(r)

  data = buf.getvalue().encode("utf-8-sig")
  headers = {"Content-Disposition": 'attachment; filename="grades.csv"'}
  return Response(content=data, media_type="text/csv; charset=utf-8", headers=headers)


@app.get("/health")
def health():
  db_state = "ok"
  mqtt_state = "ok"

  try:
    with get_conn() as conn, conn.cursor() as cur:
      cur.execute("select 1")
      cur.fetchone()
  except Exception as exc:
    db_state = f"error:{type(exc).__name__}"

  try:
    client = mqtt_client()
    client.disconnect()
  except Exception as exc:
    mqtt_state = f"degraded:{type(exc).__name__}"

  status = "ok" if db_state == "ok" and mqtt_state == "ok" else "degraded"
  return {"status": status, "db": db_state, "mqtt": mqtt_state}
