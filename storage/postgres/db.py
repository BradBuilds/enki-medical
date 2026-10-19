"""
PostgreSQL database connection and schema initialization.
"""

import psycopg2
from contextlib import contextmanager
from pathlib import Path
from typing import Optional
from storage.config import get_db_dsn


@contextmanager
def get_connection(dsn: Optional[str] = None):
    """
    Get PostgreSQL connection from configured DSN.
    
    Args:
        dsn: Optional PostgreSQL connection string. If None, uses storage.config.get_db_dsn().
    
    Yields:
        psycopg2 connection object
    """
    connection_string = dsn if dsn is not None else get_db_dsn()
    conn = psycopg2.connect(connection_string)
    try:
        yield conn
    finally:
        conn.close()


def initialize_schema():
    """
    Initialize database schema from schema.sql.
    
    Idempotent: uses IF NOT EXISTS, safe to run multiple times.
    """
    schema_path = Path(__file__).parent / 'schema.sql'
    sql = schema_path.read_text(encoding='utf-8')
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
