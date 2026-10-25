"""Device um Kaufdaten erweitern (Kaufdatum + Netto-Kaufpreis) – Basis für Wert-Auswertungen in Excel."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "20261025_02_device_purchase"
down_revision = "20261025_01_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # nullable, damit bestehende Geräte und die bestehende API weiter funktionieren
    op.add_column("device", sa.Column("purchase_date", sa.Date(), nullable=True))
    op.add_column("device", sa.Column("purchase_price", sa.Numeric(10, 2), nullable=True))
    op.create_check_constraint("chk_device_purchase_price", "device", "purchase_price >= 0")

    # Bestandsdaten nachpflegen (Datenmigration)
    op.get_bind().execute(text("""
        UPDATE device d
        SET purchase_date = v.purchase_date::date, purchase_price = v.purchase_price
        FROM (VALUES
            ('SN-LAP-001', '2025-03-01', 1299.00),
            ('SN-LAP-002', '2025-06-15', 2499.00),
            ('SN-MON-001', '2024-11-20',  549.90),
            ('SN-SCN-001', '2024-02-10',  189.00),
            ('SN-SCN-002', '2024-02-10',  219.00)
        ) AS v(serial_number, purchase_date, purchase_price)
        WHERE d.serial_number = v.serial_number;
    """))


def downgrade() -> None:
    op.drop_constraint("chk_device_purchase_price", "device", type_="check")
    op.drop_column("device", "purchase_price")
    op.drop_column("device", "purchase_date")
