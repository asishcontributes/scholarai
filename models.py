import sqlite3

def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT,
        age INTEGER,
        education TEXT,
        field TEXT,
        income INTEGER,
        category TEXT,
        state TEXT,
        interests TEXT,
        documents TEXT
    )
    """)

    conn.commit()
    conn.close()

   