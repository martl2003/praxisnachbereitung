import os
import json
import threading
import time

import paho.mqtt.client as mqtt

from .db import get_conn

MQTT_HOST = os.getenv("MQTT_HOST", "mqtt")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_GRADES_TOPIC", "grades/new")


def _on_message(client: mqtt.Client, userdata, msg: mqtt.MQTTMessage):
  """Wird aufgerufen, wenn eine Nachricht auf dem Grades-Topic eingeht.

  Erwartetes Payload-Format (JSON):
  {
    "student_id": 1,
    "module_id": 2,
    "grade_value": "1,7"
  }
  """
  try:
    payload = msg.payload.decode("utf-8")
    data = json.loads(payload)
    student_id = int(data["student_id"])
    module_id = int(data["module_id"])
    grade_value = str(data["grade_value"])
  except Exception as exc:
    print("[MQTT] Ungültiges Payload, wird ignoriert:", exc)
    return

  try:
    with get_conn() as conn, conn.cursor() as cur:
      cur.execute(
        """
        insert into grade (student_id, module_id, grade_value)
        values (%s, %s, %s)
        """,
        (student_id, module_id, grade_value),
      )
    print(f"[MQTT] Neue Note angelegt: student_id={student_id}, module_id={module_id}, grade_value={grade_value}")
  except Exception as exc:
    print("[MQTT] Fehler beim Anlegen der Note:", exc)


def _mqtt_loop():
  """Verbindet sich mit dem Broker, abonniert das Topic und läuft in einer Endlosschleife."""
  while True:
    try:
      client = mqtt.Client()
      client.on_message = _on_message
      client.connect(MQTT_HOST, MQTT_PORT, keepalive=30)
      # Beispiel fuer die Kommandozeile:
      # mosquitto_pub -h localhost -p 1883 -t "grades/new" -m '{"student_id":1,"module_id":2,"grade_value":"1,0"}'
      client.subscribe(MQTT_TOPIC, qos=0)
      print(f"[MQTT] Verbunden mit {MQTT_HOST}:{MQTT_PORT}, Topic '{MQTT_TOPIC}' abonniert.")
      client.loop_forever()
    except Exception as exc:
      print("[MQTT] Verbindungsfehler, neuer Versuch in 5s:", exc)
      time.sleep(5)


def start_mqtt_listener():
  """Startet den MQTT-Listener in einem Hintergrundthread."""
  t = threading.Thread(target=_mqtt_loop, daemon=True)
  t.start()
