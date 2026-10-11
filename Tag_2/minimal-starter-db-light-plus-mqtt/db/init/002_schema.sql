BEGIN;

CREATE TABLE address (
    address_id    integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    street        varchar(200) NOT NULL,
    house_number  varchar(20)  NOT NULL,
    postal_code   varchar(20)  NOT NULL,
    city          varchar(100) NOT NULL,
    country       varchar(100) NOT NULL
);


CREATE TABLE site (
    site_id     integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    address_id  integer      NOT NULL,
    site_name   varchar(100) NOT NULL,

    CONSTRAINT uq_site_name UNIQUE (site_name),
    CONSTRAINT fk_site_address
        FOREIGN KEY (address_id) REFERENCES address (address_id)
        ON DELETE RESTRICT
);

CREATE INDEX idx_site_address_id ON site (address_id);


CREATE TABLE department (
    department_id    integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    site_id          integer      NOT NULL,
    department_name  varchar(100) NOT NULL,

    -- Derselbe Abteilungsname darf an verschiedenen Standorten existieren,
    -- pro Standort aber nur einmal.
    CONSTRAINT uq_department_site_name UNIQUE (site_id, department_name),
    CONSTRAINT fk_department_site
        FOREIGN KEY (site_id) REFERENCES site (site_id)
        ON DELETE RESTRICT
);
-- Kein separater Index auf site_id nötig: uq_department_site_name beginnt mit site_id.


CREATE TABLE employee (
    employee_id      integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    employee_number  varchar(20)  NOT NULL,
    first_name       varchar(100) NOT NULL,
    last_name        varchar(100) NOT NULL,
    department_id    integer      NOT NULL,

    CONSTRAINT uq_employee_number UNIQUE (employee_number),
    CONSTRAINT fk_employee_department
        FOREIGN KEY (department_id) REFERENCES department (department_id)
        ON DELETE RESTRICT
);

CREATE INDEX idx_employee_department_id ON employee (department_id);


CREATE TABLE device (
    device_id         integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    site_id           integer       NOT NULL,
    inventory_number  varchar(20)   NOT NULL,
    device_type       varchar(50)   NOT NULL,
    model             varchar(100)  NOT NULL,
    purchase_date     date          NOT NULL,
    purchase_price    numeric(10,2) NOT NULL,

    CONSTRAINT uq_device_inventory_number UNIQUE (inventory_number),
    CONSTRAINT chk_device_purchase_price CHECK (purchase_price >= 0),
    CONSTRAINT fk_device_site
        FOREIGN KEY (site_id) REFERENCES site (site_id)
        ON DELETE RESTRICT
);

CREATE INDEX idx_device_site_id ON device (site_id);


CREATE TABLE assignment (
    assignment_id  integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    employee_id    integer     NOT NULL,
    device_id      integer     NOT NULL,
    assigned_at    timestamptz NOT NULL DEFAULT now(),
    returned_at    timestamptz NULL,

    CONSTRAINT chk_assignment_dates
        CHECK (returned_at IS NULL OR returned_at >= assigned_at),
    CONSTRAINT fk_assignment_employee
        FOREIGN KEY (employee_id) REFERENCES employee (employee_id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_assignment_device
        FOREIGN KEY (device_id) REFERENCES device (device_id)
        ON DELETE RESTRICT
);

-- R1: Pro Gerät höchstens eine aktive Ausleihe
CREATE UNIQUE INDEX uq_assignment_active_device
    ON assignment (device_id)
    WHERE returned_at IS NULL;

-- Für Historienabfragen pro Gerät bzw. pro Person
CREATE INDEX idx_assignment_device_assigned_at ON assignment (device_id, assigned_at);
CREATE INDEX idx_assignment_employee_id        ON assignment (employee_id);

COMMIT;