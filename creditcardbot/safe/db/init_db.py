import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "creditcards.db")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # --- Schema ---

    cur.execute("""
        CREATE TABLE IF NOT EXISTS credit_cards (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            card_name     TEXT    NOT NULL,
            apr           REAL    NOT NULL,
            annual_fee    REAL    NOT NULL DEFAULT 0,
            credit_limit  INTEGER NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS applicants (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name      TEXT    NOT NULL,
            last_name       TEXT    NOT NULL,
            email           TEXT    NOT NULL UNIQUE,
            credit_score    INTEGER,
            annual_income   REAL,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            applicant_id    INTEGER NOT NULL REFERENCES applicants(id),
            card_id         INTEGER NOT NULL REFERENCES credit_cards(id),
            status          TEXT    NOT NULL DEFAULT 'pending'
                            CHECK (status IN ('pending','approved','denied','review')),
            approved_limit  INTEGER,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # --- Seed data ---

    cards = [
        # (card_name, apr, annual_fee, credit_limit)
        ("CashPlus Rewards",    21.49,   0, 10000),
        ("UltraCash Elite",     20.49,  95, 15000),
        ("Voyager Travel Card", 22.49,  95, 12000),
    ]
    cur.executemany(
        "INSERT OR IGNORE INTO credit_cards (card_name, apr, annual_fee, credit_limit) "
        "VALUES (?, ?, ?, ?)",
        cards,
    )

    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_PATH}")


if __name__ == "__main__":
    init_db()
