"""Initiales Inventar-Schema (aus db/init/010_inventory_schema.sql von Tag 3) inkl. Seed-Daten."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "20261025_01_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "department",
        sa.Column("department_id", sa.Integer(), sa.Identity(always=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.UniqueConstraint("name", name="uq_department_name"),
    )

    op.create_table(
        "person",
        sa.Column("person_id", sa.Integer(), sa.Identity(always=True), primary_key=True),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(150), nullable=True),
        sa.Column("department_id", sa.Integer(), nullable=False),
        sa.UniqueConstraint("email", name="uq_person_email"),
        sa.ForeignKeyConstraint(["department_id"], ["department.department_id"],
                                name="fk_person_department", ondelete="RESTRICT"),
    )
    op.create_index("idx_person_department_id", "person", ["department_id"])

    op.create_table(
        "device_type",
        sa.Column("device_type_id", sa.Integer(), sa.Identity(always=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.UniqueConstraint("name", name="uq_device_type_name"),
    )

    op.create_table(
        "location",
        sa.Column("location_id", sa.Integer(), sa.Identity(always=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.UniqueConstraint("name", name="uq_location_name"),
    )

    op.create_table(
        "device",
        sa.Column("device_id", sa.Integer(), sa.Identity(always=True), primary_key=True),
        sa.Column("serial_number", sa.String(100), nullable=False),
        sa.Column("device_type_id", sa.Integer(), nullable=False),
        sa.Column("location_id", sa.Integer(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        # IR-01: serial_number ist eindeutig
        sa.UniqueConstraint("serial_number", name="uq_device_serial_number"),
        sa.ForeignKeyConstraint(["device_type_id"], ["device_type.device_type_id"],
                                name="fk_device_type", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["location_id"], ["location.location_id"],
                                name="fk_device_location", ondelete="RESTRICT"),
    )
    op.create_index("idx_device_type_id", "device", ["device_type_id"])
    op.create_index("idx_device_location_id", "device", ["location_id"])

    op.create_table(
        "assignment",
        sa.Column("assignment_id", sa.Integer(), sa.Identity(always=True), primary_key=True),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("person_id", sa.Integer(), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("returned_at", sa.DateTime(timezone=True), nullable=True),
        # IR-03: returned_at darf nicht vor issued_at liegen
        sa.CheckConstraint("returned_at IS NULL OR returned_at >= issued_at", name="chk_assignment_dates"),
        sa.ForeignKeyConstraint(["device_id"], ["device.device_id"],
                                name="fk_assignment_device", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["person_id"], ["person.person_id"],
                                name="fk_assignment_person", ondelete="RESTRICT"),
    )
    # IR-02: Ein Device darf maximal eine aktive Ausleihe haben (Partial Unique Index)
    op.create_index("uq_assignment_active_device", "assignment", ["device_id"],
                    unique=True, postgresql_where=sa.text("returned_at IS NULL"))
    op.create_index("idx_assignment_device_issued_at", "assignment", ["device_id", "issued_at"])
    op.create_index("idx_assignment_person_id", "assignment", ["person_id"])

    # Seed-Daten (unverändert aus Tag 3)
    conn = op.get_bind()
    conn.execute(text("""
        INSERT INTO department (name) VALUES ('IT'), ('Logistik'), ('Vertrieb')
        ON CONFLICT (name) DO NOTHING;
    """))
    conn.execute(text("""
        INSERT INTO device_type (name) VALUES ('Laptop'), ('Monitor'), ('Handscanner')
        ON CONFLICT (name) DO NOTHING;
    """))
    conn.execute(text("""
        INSERT INTO location (name) VALUES ('Gebäude E'), ('Gebäude F'), ('Gebäude H')
        ON CONFLICT (name) DO NOTHING;
    """))
    conn.execute(text("""
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
    """))
    conn.execute(text("""
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
    """))
    conn.execute(text("""
        INSERT INTO assignment (device_id, person_id, issued_at, returned_at)
        SELECT d.device_id, p.person_id, v.issued_at::timestamptz, v.returned_at::timestamptz
        FROM (VALUES
            ('SN-LAP-001', 'anna.koch@example.com',   '2026-10-01 09:00:00+02', '2026-10-10 16:30:00+02'),
            ('SN-LAP-001', 'ben.koenig@example.com',  '2026-10-15 10:00:00+02', NULL),
            ('SN-SCN-001', 'clara.meier@example.com', '2026-10-18 08:30:00+02', NULL)
        ) AS v(serial_number, email, issued_at, returned_at)
        JOIN device d ON d.serial_number = v.serial_number
        JOIN person p ON p.email         = v.email;
    """))


def downgrade() -> None:
    op.drop_table("assignment")
    op.drop_table("device")
    op.drop_table("location")
    op.drop_table("device_type")
    op.drop_table("person")
    op.drop_table("department")
