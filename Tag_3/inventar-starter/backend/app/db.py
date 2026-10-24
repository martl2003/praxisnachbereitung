import os
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

load_dotenv()

DB_DSN = os.getenv("DB_DSN", "postgresql://appuser:apppass@db:5432/appdb")

def get_conn() -> psycopg.Connection:
    return psycopg.connect(DB_DSN, row_factory=dict_row, autocommit=True)
