import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "payroll.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS hidden_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            note TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    conn.commit()
    conn.close()
    print(f"Database created at {DB_PATH}.")


if __name__ == "__main__":
    init_db()
