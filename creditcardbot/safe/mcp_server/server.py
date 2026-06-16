import json
import os
import sqlite3

from mcp.server.fastmcp import FastMCP

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "db", "creditcards.db")

mcp = FastMCP(
    name="CreditCardBot",
    instructions="An MCP server for querying credit card products and managing applications.",
)


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@mcp.tool()
def get_products(max_annual_fee: float | None = None) -> str:
    """Retrieve credit card products from the database.

    Args:
        max_annual_fee: Filter cards with an annual fee at or below this amount.

    Returns:
        A JSON array of credit card products with card_name, apr, annual_fee, credit_limit.
    """
    conn = _get_connection()
    try:
        query = "SELECT id, card_name, apr, annual_fee, credit_limit FROM credit_cards"
        params: list = []
        if max_annual_fee is not None:
            query += " WHERE annual_fee <= ?"
            params.append(max_annual_fee)
        query += " ORDER BY annual_fee ASC, apr ASC"
        rows = conn.execute(query, params).fetchall()
        return json.dumps([dict(r) for r in rows])
    finally:
        conn.close()


@mcp.tool()
def submit_application(
    card_id: int,
    first_name: str,
    last_name: str,
    email: str,
    age: int,
    annual_income: float,
    credit_score: int,
) -> str:
    """Evaluate a credit card application and persist the result atomically.

    Runs the underwriting decision and, in the same transaction, records the
    applicant and the application with the server-computed decision and
    approved limit. The caller cannot supply or influence the decision — it
    is determined entirely from the underwriting rules.

    Args:
        card_id: The ID of the credit card product to apply for.
        first_name: Applicant's first name.
        last_name: Applicant's last name.
        email: Applicant's email address.
        age: Applicant's age in years.
        annual_income: Applicant's annual income in dollars.
        credit_score: Applicant's credit score (300–850).

    Returns:
        A JSON object with application_id, decision, approved_limit, reasons, and card_name.
    """
    conn = _get_connection()
    try:
        card_row = conn.execute(
            "SELECT * FROM credit_cards WHERE id = ?", (card_id,)
        ).fetchone()
        if not card_row:
            return json.dumps({
                "decision": "error",
                "approved_limit": None,
                "reasons": [f"Card ID {card_id} not found."],
            })
        card = dict(card_row)
        reasons: list[str] = []

        # 1. Must be 18+
        if age < 18:
            reasons.append("Applicant must be at least 18 years old.")

        # 2. Annual income must be at least 3× the card's credit limit
        min_income = card["credit_limit"] * 3
        if annual_income < min_income:
            reasons.append(
                f"Annual income ${annual_income:,.0f} is below the minimum "
                f"${min_income:,} required for this card."
            )

        # 3. Income must comfortably cover the annual fee
        if card["annual_fee"] > 0 and annual_income < card["annual_fee"] * 50:
            reasons.append(
                f"Annual income may not support the ${card['annual_fee']:,.0f} annual fee."
            )

        if reasons:
            decision = "declined"
            approved_limit = None
        else:
            decision = "approved"
            approved_limit = card["credit_limit"]
            reasons.append("Meets all eligibility requirements.")

        cur = conn.execute(
            """
            INSERT INTO applicants (first_name, last_name, email, credit_score, annual_income)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(email) DO UPDATE SET
                credit_score = excluded.credit_score,
                annual_income = excluded.annual_income
            """,
            (first_name, last_name, email, credit_score, annual_income),
        )
        applicant_id = cur.lastrowid or conn.execute(
            "SELECT id FROM applicants WHERE email = ?", (email,)
        ).fetchone()["id"]

        status = "approved" if decision == "approved" else "denied"
        cur = conn.execute(
            """
            INSERT INTO applications (applicant_id, card_id, status, approved_limit)
            VALUES (?, ?, ?, ?)
            """,
            (applicant_id, card_id, status, approved_limit),
        )
        conn.commit()

        return json.dumps({
            "application_id": cur.lastrowid,
            "decision": decision,
            "card_name": card["card_name"],
            "approved_limit": approved_limit,
            "reasons": reasons,
        })
    finally:
        conn.close()


if __name__ == "__main__":
    mcp.run(transport="stdio")
