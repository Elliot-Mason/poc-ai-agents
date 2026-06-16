import json
import sqlite3
from pathlib import Path

from mcp.server.fastmcp import FastMCP

DB_PATH = Path(__file__).parent.parent / "mortgage.db"

mcp = FastMCP("mortgage-rates")


@mcp.tool()
def get_rates(
    loan_type: str | None = None,
    term_years: int | None = None,
    max_rate: float | None = None,
) -> str:
    """Get mortgage rates with optional filters.

    Args:
        loan_type: Filter by loan type (variable, fixed, interest_only).
        term_years: Filter by loan term in years.
        max_rate: Filter by maximum interest rate.
    """
    query = "SELECT * FROM rates"
    conditions = []
    params = []

    if loan_type is not None:
        conditions.append("loan_type = ?")
        params.append(loan_type)
    if term_years is not None:
        conditions.append("term_years = ?")
        params.append(term_years)
    if max_rate is not None:
        conditions.append("rate <= ?")
        params.append(max_rate)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(query, params).fetchall()
        return json.dumps([dict(row) for row in rows])
    finally:
        conn.close()


@mcp.tool()
def create_quote(loan_type: str, rate: float) -> str:
    """Create a mortgage quote for a user.

    Args:
        loan_type: The loan type (variable, fixed, interest_only).
        rate: The agreed interest rate.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        valid = conn.execute(
            "SELECT 1 FROM rates WHERE loan_type = ? AND rate = ?",
            (loan_type, rate),
        ).fetchone()
        if not valid:
            return json.dumps({
                "error": f"Rate {rate}% is not available for {loan_type} loans. "
                "Please use get_rates to find valid rates."
            })
        cur = conn.execute(
            "INSERT INTO quotes (loan_type, rate) VALUES (?, ?) RETURNING *",
            (loan_type, rate),
        )
        row = cur.fetchone()
        conn.commit()
        return json.dumps(dict(row))
    finally:
        conn.close()


if __name__ == "__main__":
    mcp.run(transport="stdio")
