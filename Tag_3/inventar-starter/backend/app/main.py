from datetime import datetime, timezone
import os
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import paho.mqtt.client as mqtt
import psycopg.errors
from pydantic import ValidationError

from .db import get_conn
from .models import (
    AssignmentCreate,
    AssignmentOut,
    AssignmentReturn,
    DeviceCreate,
    DeviceOut,
    DeviceUpdate,
)

app = FastAPI(title="Inventar Starter", version="0.1.0")
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

MQTT_HOST = os.getenv("MQTT_HOST", "mqtt")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))


def mqtt_client() -> mqtt.Client:
    c = mqtt.Client()
    c.connect(MQTT_HOST, MQTT_PORT, keepalive=30)
    return c


def parse_timestamp(value: str | None, field_name: str) -> datetime | None:
    if value is None or str(value).strip() == "":
        return None
    raw = str(value).strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Ungültiges Zeitformat für {field_name}: '{value}'",
        ) from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


async def parse_payload(request: Request, model_cls, allow_empty: bool = False):
    content_type = request.headers.get("content-type", "")
    try:
        if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
            form = await request.form()
            raw_data = {k: (v if v != "" else None) for k, v in form.items()}
        else:
            body = await request.body()
            if not body:
                if allow_empty:
                    raw_data = {}
                else:
                    raise HTTPException(status_code=422, detail="Request-Body fehlt.")
            else:
                raw_data = await request.json()
        return model_cls(**raw_data)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def fetch_devices(cur) -> list[dict]:
    cur.execute(
        """
        SELECT d.device_id,
               d.serial_number,
               d.device_type_id,
               dt.name AS device_type_name,
               d.location_id,
               l.name AS location_name,
               d.note,
               CASE WHEN a.assignment_id IS NOT NULL THEN 'ausgeliehen' ELSE 'frei' END AS status
        FROM device d
        JOIN device_type dt ON dt.device_type_id = d.device_type_id
        JOIN location l     ON l.location_id     = d.location_id
        LEFT JOIN assignment a
               ON a.device_id = d.device_id AND a.returned_at IS NULL
        ORDER BY d.device_id
        """
    )
    return list(cur.fetchall())


def fetch_device_by_id(cur, device_id: int) -> dict | None:
    cur.execute(
        """
        SELECT d.device_id,
               d.serial_number,
               d.device_type_id,
               dt.name AS device_type_name,
               d.location_id,
               l.name AS location_name,
               d.note,
               CASE WHEN a.assignment_id IS NOT NULL THEN 'ausgeliehen' ELSE 'frei' END AS status
        FROM device d
        JOIN device_type dt ON dt.device_type_id = d.device_type_id
        JOIN location l     ON l.location_id     = d.location_id
        LEFT JOIN assignment a
               ON a.device_id = d.device_id AND a.returned_at IS NULL
        WHERE d.device_id = %s
        """,
        (device_id,),
    )
    return cur.fetchone()


def fetch_assignments(cur, active_only: bool = False) -> list[dict]:
    where_clause = "WHERE a.returned_at IS NULL" if active_only else ""
    cur.execute(
        f"""
        SELECT a.assignment_id,
               a.device_id,
               d.serial_number,
               dt.name AS device_type_name,
               a.person_id,
               (p.first_name || ' ' || p.last_name) AS person_name,
               a.issued_at,
               a.returned_at
        FROM assignment a
        JOIN device d       ON d.device_id       = a.device_id
        JOIN device_type dt ON dt.device_type_id = d.device_type_id
        JOIN person p       ON p.person_id       = a.person_id
        {where_clause}
        ORDER BY a.issued_at DESC, a.assignment_id DESC
        """
    )
    return list(cur.fetchall())


def fetch_assignment_by_id(cur, assignment_id: int) -> dict | None:
    cur.execute(
        """
        SELECT a.assignment_id,
               a.device_id,
               d.serial_number,
               dt.name AS device_type_name,
               a.person_id,
               (p.first_name || ' ' || p.last_name) AS person_name,
               a.issued_at,
               a.returned_at
        FROM assignment a
        JOIN device d       ON d.device_id       = a.device_id
        JOIN device_type dt ON dt.device_type_id = d.device_type_id
        JOIN person p       ON p.person_id       = a.person_id
        WHERE a.assignment_id = %s
        """,
        (assignment_id,),
    )
    return cur.fetchone()


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


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "title": "Inventar Starter"})


@app.get("/inventory", response_class=HTMLResponse)
async def inventory_page(request: Request):
    return templates.TemplateResponse("inventory.html", {"request": request, "title": "Inventar Starter"})


@app.get("/devices", response_model=list[DeviceOut])
async def list_devices():
    with get_conn() as conn, conn.cursor() as cur:
        return fetch_devices(cur)


@app.get("/devices/{device_id}", response_model=DeviceOut)
async def get_device(device_id: int):
    with get_conn() as conn, conn.cursor() as cur:
        row = fetch_device_by_id(cur, device_id)
    if not row:
        raise HTTPException(status_code=404, detail="Device nicht gefunden.")
    return row


@app.post(
    "/devices",
    response_model=DeviceOut,
    status_code=201,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {"schema": DeviceCreate.model_json_schema()},
                "application/x-www-form-urlencoded": {"schema": DeviceCreate.model_json_schema()},
            },
        }
    },
)
async def create_device(request: Request):
    data: DeviceCreate = await parse_payload(request, DeviceCreate)
    serial = data.serial_number.strip()
    if not serial:
        raise HTTPException(status_code=422, detail="serial_number darf nicht leer sein.")

    try:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO device (serial_number, device_type_id, location_id, note)
                VALUES (%s, %s, %s, %s)
                RETURNING device_id
                """,
                (serial, data.device_type_id, data.location_id, data.note),
            )
            created = cur.fetchone()
            device = fetch_device_by_id(cur, created["device_id"])
    except psycopg.errors.UniqueViolation as exc:
        # IR-01: serial_number ist eindeutig
        raise HTTPException(
            status_code=409,
            detail=f"IR-01 verletzt: Seriennummer '{serial}' existiert bereits.",
        ) from exc
    except psycopg.errors.ForeignKeyViolation as exc:
        raise HTTPException(
            status_code=422,
            detail="Ungültige device_type_id oder location_id.",
        ) from exc

    return JSONResponse(status_code=201, content=device)


@app.put(
    "/devices/{device_id}",
    response_model=DeviceOut,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {"schema": DeviceUpdate.model_json_schema()},
                "application/x-www-form-urlencoded": {"schema": DeviceUpdate.model_json_schema()},
            },
        }
    },
)
async def update_device(device_id: int, request: Request):
    data: DeviceUpdate = await parse_payload(request, DeviceUpdate)
    serial = data.serial_number.strip()
    if not serial:
        raise HTTPException(status_code=422, detail="serial_number darf nicht leer sein.")

    try:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE device
                SET serial_number  = %s,
                    device_type_id = %s,
                    location_id    = %s,
                    note           = %s
                WHERE device_id = %s
                RETURNING device_id
                """,
                (serial, data.device_type_id, data.location_id, data.note, device_id),
            )
            updated = cur.fetchone()
            if not updated:
                raise HTTPException(status_code=404, detail="Device nicht gefunden.")
            device = fetch_device_by_id(cur, device_id)
    except psycopg.errors.UniqueViolation as exc:
        raise HTTPException(
            status_code=409,
            detail=f"IR-01 verletzt: Seriennummer '{serial}' existiert bereits.",
        ) from exc
    except psycopg.errors.ForeignKeyViolation as exc:
        raise HTTPException(
            status_code=422,
            detail="Ungültige device_type_id oder location_id.",
        ) from exc

    return device


@app.delete("/devices/{device_id}")
async def delete_device(device_id: int):
    try:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM device WHERE device_id = %s RETURNING device_id", (device_id,))
            deleted = cur.fetchone()
            if not deleted:
                raise HTTPException(status_code=404, detail="Device nicht gefunden.")
    except psycopg.errors.ForeignKeyViolation as exc:
        raise HTTPException(
            status_code=409,
            detail="Device kann nicht gelöscht werden, da Ausleihen zu diesem Gerät existieren.",
        ) from exc
    return {"ok": True, "deleted_device_id": device_id}


@app.get("/assignments", response_model=list[AssignmentOut])
async def list_assignments():
    with get_conn() as conn, conn.cursor() as cur:
        return fetch_assignments(cur, active_only=False)


@app.get("/assignments/active", response_model=list[AssignmentOut])
async def list_active_assignments():
    with get_conn() as conn, conn.cursor() as cur:
        return fetch_assignments(cur, active_only=True)


@app.post(
    "/assignments",
    response_model=AssignmentOut,
    status_code=201,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {"schema": AssignmentCreate.model_json_schema()},
                "application/x-www-form-urlencoded": {"schema": AssignmentCreate.model_json_schema()},
            },
        }
    },
)
async def create_assignment(request: Request):
    data: AssignmentCreate = await parse_payload(request, AssignmentCreate)
    issued_dt = parse_timestamp(data.issued_at, "issued_at")

    try:
        with get_conn() as conn, conn.cursor() as cur:
            # Prüfen, ob Device bereits aktiv ausgeliehen ist (IR-02)
            cur.execute(
                "SELECT assignment_id FROM assignment WHERE device_id = %s AND returned_at IS NULL",
                (data.device_id,),
            )
            if cur.fetchone():
                raise HTTPException(
                    status_code=409,
                    detail=f"IR-02 verletzt: Device {data.device_id} hat bereits eine aktive Ausleihe.",
                )

            if issued_dt is not None:
                cur.execute(
                    """
                    INSERT INTO assignment (device_id, person_id, issued_at)
                    VALUES (%s, %s, %s)
                    RETURNING assignment_id
                    """,
                    (data.device_id, data.person_id, issued_dt),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO assignment (device_id, person_id)
                    VALUES (%s, %s)
                    RETURNING assignment_id
                    """,
                    (data.device_id, data.person_id),
                )
            created = cur.fetchone()
            assignment = fetch_assignment_by_id(cur, created["assignment_id"])
    except psycopg.errors.UniqueViolation as exc:
        # IR-02 auf DB-Ebene (uq_assignment_active_device)
        raise HTTPException(
            status_code=409,
            detail=f"IR-02 verletzt: Device {data.device_id} hat bereits eine aktive Ausleihe.",
        ) from exc
    except psycopg.errors.ForeignKeyViolation as exc:
        raise HTTPException(
            status_code=422,
            detail="Ungültige device_id oder person_id.",
        ) from exc

    return assignment


@app.post(
    "/assignments/{assignment_id}/return",
    response_model=AssignmentOut,
    openapi_extra={
        "requestBody": {
            "required": False,
            "content": {
                "application/json": {"schema": AssignmentReturn.model_json_schema()},
                "application/x-www-form-urlencoded": {"schema": AssignmentReturn.model_json_schema()},
            },
        }
    },
)
async def return_assignment(assignment_id: int, request: Request):
    data: AssignmentReturn = await parse_payload(request, AssignmentReturn, allow_empty=True)
    returned_dt = parse_timestamp(data.returned_at, "returned_at")

    try:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT assignment_id, issued_at, returned_at FROM assignment WHERE assignment_id = %s",
                (assignment_id,),
            )
            existing = cur.fetchone()
            if not existing:
                raise HTTPException(status_code=404, detail="Ausleihe nicht gefunden.")
            if existing["returned_at"] is not None:
                raise HTTPException(status_code=409, detail="Ausleihe wurde bereits zurückgegeben.")

            effective_return = returned_dt or datetime.now(timezone.utc)
            # IR-03: returned_at darf nicht vor issued_at liegen
            if effective_return < existing["issued_at"]:
                raise HTTPException(
                    status_code=422,
                    detail="IR-03 verletzt: returned_at darf nicht vor issued_at liegen.",
                )

            cur.execute(
                """
                UPDATE assignment
                SET returned_at = %s
                WHERE assignment_id = %s
                """,
                (effective_return, assignment_id),
            )
            assignment = fetch_assignment_by_id(cur, assignment_id)
    except psycopg.errors.CheckViolation as exc:
        raise HTTPException(
            status_code=422,
            detail="IR-03 verletzt: returned_at darf nicht vor issued_at liegen.",
        ) from exc

    return assignment


@app.post("/mqtt/publish")
async def mqtt_publish(topic: str = Query(...), payload: str = Query(...)):
    c = mqtt_client()
    c.publish(topic, payload, qos=0, retain=False)
    c.disconnect()
    return {"ok": True, "topic": topic, "payload": payload}

