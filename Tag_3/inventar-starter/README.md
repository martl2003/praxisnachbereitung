# Inventar Starter

Arbeitsbasis für **Tag 3**. Dieses Projekt ist bewusst **nicht fertig**, sondern soll euch einen praktikablen Einstieg geben:

- Infrastruktur ist vorbereitet
- UI- und Form-Support ist vorhanden
- MQTT kann sofort getestet werden
- die eigentliche Inventar-Domäne baut ihr selbst

Der `grades-starter` dient daneben als **Referenzprojekt** für Struktur, Formulare, Templates und CRUD-Muster.

## Enthalten

- FastAPI
- PostgreSQL
- MQTT (Eclipse Mosquitto)
- Jinja-Templates
- `python-multipart` für HTML-Formulare
- Startseite, `/health`, `/docs`, `/inventory`
- MQTT-Publish-Endpunkt `/mqtt/publish`

## Schnellstart

```bash
docker compose up -d --build
```

Danach prüfen:

```bash
open http://localhost:8000/
open http://localhost:8000/health
open http://localhost:8000/inventory
open http://localhost:8000/docs
```

## Eure Aufgabe

Ergänzt in diesem Projekt:

- das Inventar-Schema in `db/init/010_inventory_schema.sql`
- Seed-Daten für eure Domäne
- Endpunkte für `devices` und `assignments`
- Domänenregeln wie eindeutige Seriennummern und max. eine aktive Ausleihe
- eine einfache Inventar-Oberfläche

## MQTT testen

Subscriber:

```bash
mosquitto_sub -h localhost -t "inventory/#" -v
```

Publish über die API:

```bash
curl -X POST "http://localhost:8000/mqtt/publish?topic=inventory/test&payload=hello"
```
