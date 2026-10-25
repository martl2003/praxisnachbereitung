# Excel-Auswertung der Inventar-App (Power Query + Pivot)

Datenquelle ist die flache Ausleih-Tabelle der API (eine Zeile pro Ausleihe inkl. Gerät, Standort, Person, Abteilung):

| Variante | URL | Wofür |
|---|---|---|
| A – CSV-Endpoint | `http://localhost:8000/assignments.csv` | Power Query „Aus dem Web“, immer frische Daten |
| C – XLSX-Export | `http://localhost:8000/assignments.xlsx` | Datei für Fachbereiche, Datentypen bleiben erhalten |

Spalten: `assignment_id, serial_number, device_type, location, model, purchase_price, person_name, department, issued_date, issued_time, returned_date, returned_time, status, duration_days`

## Pipeline 1 – Power Query direkt auf den CSV-Endpoint

1. Excel → **Daten** → **Aus dem Web** → URL `http://localhost:8000/assignments.csv`
2. Im Vorschaufenster: Trennzeichen **Semikolon**, Dateiursprung **65001: Unicode (UTF-8)** → **Daten transformieren**
3. Datentypen prüfen bzw. setzen:
   - `assignment_id` → Ganze Zahl
   - `purchase_price`, `duration_days` → Dezimalzahl (die API liefert Dezimalkomma)
   - `issued_date`, `returned_date` → Datum
   - `issued_time`, `returned_time` → Uhrzeit
   - Rest → Text
4. **Schließen & laden in…** → **Nur Verbindung erstellen** + **Dem Datenmodell hinzufügen**
5. Aktualisieren: **Daten → Alle aktualisieren**. Excel holt sich die aktuellen Daten von der API, kein manueller Export nötig.

## Pipeline 2 – Power Query auf die XLSX-Datei

1. `http://localhost:8000/assignments.xlsx` herunterladen (z. B. nach `excel/assignments.xlsx`)
2. In einer separaten Datei `inventory_report.xlsx`: **Daten → Daten abrufen → Aus Datei → Aus Arbeitsmappe** → Blatt `Ausleihen`
3. Weiter wie oben ab Schritt 4

Vorteil: Datenlieferant und Reporting-Arbeitsmappe sind getrennt. Nachteil: Die Datei muss neu heruntergeladen werden (dasselbe „CSV-Schieberei“-Problem wie Variante B).

## Pivot-Auswertungen (Vorschläge)

| Frage | Zeilen | Spalten | Werte | Filter |
|---|---|---|---|---|
| Wie viele Ausleihen pro Gerätetyp? | `device_type` | – | Anzahl `assignment_id` | – |
| Wie verteilen sich Ausleihen auf Standorte und Typen? | `device_type` | `location` | Anzahl `assignment_id` | – |
| Welche Abteilung leiht am meisten aus? | `department` | `status` | Anzahl `assignment_id` | – |
| Wie lange werden Geräte im Schnitt ausgeliehen? | `device_type` | – | Mittelwert `duration_days` | `status = zurückgegeben` |
| Welcher Gerätewert ist aktuell ausgeliehen? | `location` | – | Summe `purchase_price` | `status = aktiv` |

Dazu jeweils ein **PivotChart** (z. B. gestapeltes Säulendiagramm für Typ × Standort).

**Wichtig:** Die PivotTable ist nur eine Sicht. Stabil wird die Auswertung durch die Pipeline (API → Power Query → Datenmodell). Gleiche Daten in der DB ergeben nach „Aktualisieren“ das gleiche Ergebnis.
