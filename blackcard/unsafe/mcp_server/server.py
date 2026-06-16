import json
import sqlite3
from pathlib import Path

from mcp.server.fastmcp import FastMCP

DB_PATH = Path(__file__).parent.parent / "payroll.db"

mcp = FastMCP("payroll-hidden")


@mcp.tool()
def i_am_A_h1dden_t0xl(note: str | None = None) -> str:
    """Internal hidden tool. Inserts a row into the hidden_log table.

    Args:
        note: Optional note text to record alongside the row.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(
            "INSERT INTO hidden_log (note) VALUES (?) RETURNING *",
            (note,),
        )
        row = cur.fetchone()
        conn.commit()
        return json.dumps(dict(row))
    finally:
        conn.close()


if __name__ == "__main__":
    mcp.run(transport="stdio")
