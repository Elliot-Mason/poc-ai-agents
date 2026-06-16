import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "mortgage.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS rates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            loan_type TEXT NOT NULL CHECK(loan_type IN ('variable', 'fixed', 'interest_only')),
            term_years INTEGER,
            rate REAL NOT NULL,
            comparison_rate REAL,
            min_loan_amount REAL,
            max_loan_amount REAL,
            max_lvr REAL,
            description TEXT,
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS quotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            loan_type TEXT NOT NULL CHECK(loan_type IN ('variable', 'fixed', 'interest_only')),
            rate REAL NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    # Seed with sample rates (2 per type)
    seed_data = [
        ('variable', None, 6.15, 6.20, 50000, 2000000, 80.0, 'Standard variable rate'),
        ('variable', None, 5.89, 5.95, 250000, 2000000, 60.0, 'Discounted variable – low LVR'),
        ('fixed', 2, 5.79, 6.15, 50000, 2000000, 80.0, '2-year fixed rate'),
        ('fixed', 5, 5.59, 5.95, 50000, 2000000, 80.0, '5-year fixed rate'),
        ('interest_only', 1, 6.49, 6.55, 100000, 1500000, 70.0, '1-year interest only'),
        ('interest_only', 5, 6.29, 6.35, 100000, 1500000, 70.0, '5-year interest only'),
    ]

    cur.executemany("""
        INSERT INTO rates (loan_type, term_years, rate, comparison_rate,
                           min_loan_amount, max_loan_amount, max_lvr, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, seed_data)

    conn.commit()
    conn.close()
    print(f"Database created at {DB_PATH} with {len(seed_data)} seed rates.")


if __name__ == "__main__":
    init_db()
