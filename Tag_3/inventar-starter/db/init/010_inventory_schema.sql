-- 010_inventory_schema.sql
-- Inventar-Schema (Tag 3) inkl. Domänenregeln (IR-01, IR-02, IR-03) und Seed-Daten

BEGIN;

CREATE TABLE department (
    department_id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name          varchar(100) NOT NULL,

    CONSTRAINT uq_department_name UNIQUE (name)
);

CREATE TABLE person (
    person_id     integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    first_name    varchar(100) NOT NULL,
    last_name     varchar(100) NOT NULL,
    email         varchar(150) NULL,
    department_id integer      NOT NULL,

    CONSTRAINT uq_person_email UNIQUE (email),
    CONSTRAINT fk_person_department
        FOREIGN KEY (department_id) REFERENCES department (department_id)
        ON DELETE RESTRICT
);

CREATE INDEX idx_person_department_id ON person (department_id);

CREATE TABLE device_type (
    device_type_id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name           varchar(100) NOT NULL,

    CONSTRAINT uq_device_type_name UNIQUE (name)
);

CREATE TABLE location (
    location_id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        varchar(100) NOT NULL,

    CONSTRAINT uq_location_name UNIQUE (name)
);

CREATE TABLE device (
    device_id      integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    serial_number  varchar(100) NOT NULL,
    device_type_id integer      NOT NULL,
    location_id    integer      NOT NULL,
    note           text         NULL,

    -- IR-01: serial_number ist eindeutig
    CONSTRAINT uq_device_serial_number UNIQUE (serial_number),
    CONSTRAINT fk_device_type
        FOREIGN KEY (device_type_id) REFERENCES device_type (device_type_id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_device_location
        FOREIGN KEY (location_id) REFERENCES location (location_id)
        ON DELETE RESTRICT
);

CREATE INDEX idx_device_type_id     ON device (device_type_id);
CREATE INDEX idx_device_location_id ON device (location_id);

CREATE TABLE assignment (
    assignment_id integer     GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    device_id     integer     NOT NULL,
    person_id     integer     NOT NULL,
    issued_at     timestamptz NOT NULL DEFAULT now(),
    returned_at   timestamptz NULL,

    -- IR-03: returned_at darf nicht vor issued_at liegen
    CONSTRAINT chk_assignment_dates
        CHECK (returned_at IS NULL OR returned_at >= issued_at),
    CONSTRAINT fk_assignment_device
        FOREIGN KEY (device_id) REFERENCES device (device_id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_assignment_person
        FOREIGN KEY (person_id) REFERENCES person (person_id)
        ON DELETE RESTRICT
);

-- IR-02: Ein Device darf maximal eine aktive Ausleihe haben
CREATE UNIQUE INDEX uq_assignment_active_device
    ON assignment (device_id)
    WHERE returned_at IS NULL;

CREATE INDEX idx_assignment_device_issued_at ON assignment (device_id, issued_at);
CREATE INDEX idx_assignment_person_id        ON assignment (person_id);

-- ============================================================
-- Seed-Daten
-- ============================================================

INSERT INTO department (name) VALUES
    ('IT'),
    ('Logistik'),
    ('Vertrieb')
ON CONFLICT (name) DO NOTHING;

INSERT INTO device_type (name) VALUES
    ('Laptop'),
    ('Monitor'),
    ('Handscanner')
ON CONFLICT (name) DO NOTHING;

INSERT INTO location (name) VALUES
    ('Gebäude E'),
    ('Gebäude F'),
    ('Gebäude H')
ON CONFLICT (name) DO NOTHING;

INSERT INTO person (first_name, last_name, email, department_id)
SELECT v.first_name, v.last_name, v.email, d.department_id
FROM (VALUES
    ('Anna',  'Koch',   'anna.koch@example.com',   'IT'),
    ('Ben',   'König',  'ben.koenig@example.com',  'Logistik'),
    ('Clara', 'Meier',  'clara.meier@example.com', 'Vertrieb'),
    ('Lukas', 'Weber',  'lukas.weber@example.com', 'IT')
) AS v(first_name, last_name, email, dept_name)
JOIN department d ON d.name = v.dept_name
ON CONFLICT (email) DO NOTHING;

INSERT INTO device (serial_number, device_type_id, location_id, note)
SELECT v.serial_number, dt.device_type_id, l.location_id, v.note
FROM (VALUES
    ('SN-LAP-001', 'Laptop',      'Gebäude E', 'ThinkPad T14 Gen 4'),
    ('SN-LAP-002', 'Laptop',      'Gebäude F', 'MacBook Pro 14'),
    ('SN-MON-001', 'Monitor',     'Gebäude E', 'Dell UltraSharp 27"'),
    ('SN-SCN-001', 'Handscanner', 'Gebäude H', 'Zebra DS2208'),
    ('SN-SCN-002', 'Handscanner', 'Gebäude H', 'Honeywell Voyager 1202g')
) AS v(serial_number, type_name, loc_name, note)
JOIN device_type dt ON dt.name = v.type_name
JOIN location l     ON l.name  = v.loc_name
ON CONFLICT (serial_number) DO NOTHING;

-- Eine abgeschlossene Ausleihe (Historie) und zwei aktive Ausleihen
INSERT INTO assignment (device_id, person_id, issued_at, returned_at)
SELECT d.device_id, p.person_id, v.issued_at::timestamptz, v.returned_at::timestamptz
FROM (VALUES
    ('SN-LAP-001', 'anna.koch@example.com',   '2026-10-01 09:00:00+02', '2026-10-10 16:30:00+02'),
    ('SN-LAP-001', 'ben.koenig@example.com',  '2026-10-15 10:00:00+02', NULL),
    ('SN-SCN-001', 'clara.meier@example.com', '2026-10-18 08:30:00+02', NULL)
) AS v(serial_number, email, issued_at, returned_at)
JOIN device d ON d.serial_number = v.serial_number
JOIN person p ON p.email         = v.email;

COMMIT;

