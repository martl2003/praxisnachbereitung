# Minimal Starter – DB-Light + MQTT (FastAPI + Postgres + Mosquitto)

Kleiner Stack für die Vorlesung: **API + Postgres** und zusätzlich **MQTT-Broker** (Eclipse Mosquitto) inkl. Mini-Publish-Endpoint.
- **Kein ORM**, einfache SQL-Reports
- **CSV-Export** Excel-freundlich (`;`, `utf-8-sig`)
- **MQTT** für Event-Demo (anonym, nur für die Übung)

## Schnellstart
```bash
docker compose up -d --build
# prüfen
open http://localhost:8000/                             # UI
open http://localhost:8000/health                       # {"status":"ok","db":"ok","mqtt":"ok|degraded"}
open http://localhost:8000/reports/student-status       # JSON
open http://localhost:8000/reports/student-status.csv   # CSV-Download
```

## MQTT testen
1) **Abonnieren** (im Container):
```bash
docker compose exec mqtt sh
mosquitto_sub -h localhost -t "demo/#" -v
```
2) **Publizieren** (HTTP → API → Broker):
```bash
curl -X POST "http://localhost:8000/mqtt/publish?topic=demo/test&payload=hello"
```

Optional: WebSockets Port 9001 ist aktiviert (für Browser-Clients).
