import sqlite3
from contextlib import contextmanager

db_path="D:\Python\Broker_RAG\db\hr.db"

@contextmanager
def get_db():
    conn=sqlite3.connect(db_path)
    conn.row_factory=sqlite3.Row
    try:
        yield conn
    finally:
        conn.close