import sqlite3

def init_db():
    conn = sqlite3.connect("keys.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS api_keys (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        api_key TEXT UNIQUE,
        quota INTEGER,
        used INTEGER,
        customer_email TEXT,
        customer_id TEXT
    )''')
    conn.commit()
    conn.close()

init_db()
