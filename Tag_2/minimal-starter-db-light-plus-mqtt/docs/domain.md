# Domänenmodell Inventar

## ER-Modell

## Konzeptionelles ER-Modell

```mermaid
erDiagram
    ADDRESS ||--o{ SITE : locates

    SITE ||--o{ DEPARTMENT : contains
    SITE ||--o{ DEVICE : stores

    DEPARTMENT ||--o{ EMPLOYEE : employs

    EMPLOYEE ||--o{ ASSIGNMENT : borrows
    DEVICE ||--o{ ASSIGNMENT : assigned_via

    ADDRESS {
        int address_id PK
        string street
        string house_number
        string postal_code
        string city
        string country
    }

    SITE {
        int site_id PK
        int address_id FK
        string site_name UK
    }

    DEPARTMENT {
        int department_id PK
        int site_id FK
        string department_name
    }

    EMPLOYEE {
        int employee_id PK
        string employee_number UK
        string first_name
        string last_name
        int department_id FK
    }

    DEVICE {
        int device_id PK
        int site_id FK
        string inventory_number UK
        string device_type
        string model
        date purchase_date
        decimal purchase_price
    }

    ASSIGNMENT {
        int assignment_id PK
        int employee_id FK
        int device_id FK
        datetime assigned_at
        datetime returned_at
    }
```


## Fachregeln

- **R1:** Ein Gerät darf gleichzeitig höchstens eine aktive Ausleihe besitzen.
- **R2:** Eine aktive Ausleihe besitzt kein Rückgabedatum.
- **R3:** Das Rückgabedatum darf nicht vor dem Ausgabedatum liegen.
- **R4:** Abgeschlossene Ausleihen bleiben zur Abbildung der Historie erhalten.
- **R5:** Mitarbeitende gehören einer Abteilung an; Geräte sind einem Standort zugeordnet.

## Constraints / UK-Ideen

- `SITE.site_name` → `UNIQUE`
- `EMPLOYEE.employee_number` → `UNIQUE`
- `DEVICE.inventory_number` → `UNIQUE`
- `(DEPARTMENT.site_id, DEPARTMENT.department_name)` → `UNIQUE`
- `ASSIGNMENT.employee_id` → `FOREIGN KEY` auf `EMPLOYEE.employee_id`
- `ASSIGNMENT.device_id` → `FOREIGN KEY` auf `DEVICE.device_id`
- `CHECK (returned_at IS NULL OR returned_at >= assigned_at)`
- Pro `device_id` darf maximal eine aktive `ASSIGNMENT` mit `returned_at IS NULL` existieren.