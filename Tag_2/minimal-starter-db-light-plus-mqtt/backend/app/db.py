import os
import psycopg
from psycopg.rows import dict_row

DB_HOST = os.getenv("POSTGRES_HOST", "db")
DB_PORT = int(os.getenv("POSTGRES_CONTAINER_PORT", "5432"))
DB_NAME = os.getenv("POSTGRES_DB", "appdb")
DB_USER = os.getenv("POSTGRES_USER", "appuser")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "apppass")


def get_conn() -> psycopg.Connection:
    return psycopg.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        row_factory=dict_row,
        autocommit=True,
    )