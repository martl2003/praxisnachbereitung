from fastapi import FastAPI, Request, Response, Query
from fastapi.templating import Jinja2Templates
import os, io, csv
from .db import get_conn
import paho.mqtt.client as mqtt

app = FastAPI(title="DB-Light + MQTT Starter", version="0.3.0")
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

MQTT_HOST = os.getenv("MQTT_HOST", "mqtt")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))

def mqtt_client() -> mqtt.Client:
    c = mqtt.Client()
    c.connect(MQTT_HOST, MQTT_PORT, keepalive=30)
    return c

@app.get("/health")
async def health():
    db_state = "ok"
    mqtt_state = "ok"
    try:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("select 1")
            cur.fetchone()
    except Exception as ex:
        db_state = f"error:{type(ex).__name__}"

    try:
        c = mqtt_client()
        c.disconnect()
    except Exception as ex:
        mqtt_state = f"degraded:{type(ex).__name__}"

    return {"status": "ok" if db_state == "ok" else "degraded", "db": db_state, "mqtt": mqtt_state}

@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "title": "DB-Light + MQTT Starter"})

@app.get("/reports/student-status")
async def student_status():
    sql = """
    select semester, cnt
    from v_student_status
    order by semester;
    """
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()
    return rows

@app.get("/reports/student-status.csv")
async def student_status_csv():
    sql = """
    select semester, cnt
    from v_student_status
    order by semester;
    """
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["semester", "cnt"], delimiter=";", lineterminator="\n")
    writer.writeheader()
    for r in rows:
        writer.writerow(r)

    data = buf.getvalue().encode("utf-8-sig")
    headers = {"Content-Disposition": 'attachment; filename="student-status.csv"'}
    return Response(content=data, media_type="text/csv; charset=utf-8", headers=headers)

@app.post("/mqtt/publish")
async def mqtt_publish(topic: str = Query(...), payload: str = Query(...)):
    c = mqtt_client()
    c.publish(topic, payload, qos=0, retain=False)
    c.disconnect()
    return {"ok": True, "topic": topic, "payload": payload}
