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
def get_products(max_annual_fee: float | None = None) -> list[dict]:
    """Retrieve credit card products from the database.

    Args:
        max_annual_fee: Filter cards with an annual fee at or below this amount.

    Returns:
        A list of credit card products with card_name, apr, annual_fee, credit_limit.
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
        return [dict(r) for r in rows]
    finally:
        conn.close()


@mcp.tool()
def apply_for_card(
    card_id: int,
    age: int,
    annual_income: float,
    credit_score: int,
) -> dict:
    """Run the decision engine for a credit card application.

    Evaluates eligibility against the card's requirements and returns
    an approval or decline with reasons.

    Args:
        card_id: The ID of the credit card product to apply for.
        age: Applicant's age in years.
        annual_income: Applicant's annual income in dollars.
        credit_score: Applicant's credit score (300–850).

    Returns:
        A dict with decision, approved_limit (if approved), and reasons.
    """
    conn = _get_connection()
    try:
        card = conn.execute(
            "SELECT * FROM credit_cards WHERE id = ?", (card_id,)
        ).fetchone()
        if not card:
            return {"decision": "error", "reasons": [f"Card ID {card_id} not found."]}

        card = dict(card)
        reasons: list[str] = []

        if age < 18:
            reasons.append("Applicant must be at least 18 years old.")

        min_income = card["credit_limit"] * 3
        if annual_income < min_income:
            reasons.append(
                f"Annual income ${annual_income:,.0f} is below the minimum "
                f"${min_income:,} required for this card."
            )

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

        return {
            "decision": decision,
            "card_name": card["card_name"],
            "approved_limit": approved_limit,
            "reasons": reasons,
        }
    finally:
        conn.close()


@mcp.tool()
def save_application(
    card_id: int,
    first_name: str,
    last_name: str,
    email: str,
    annual_income: float,
    credit_score: int,
    decision: str,
    approved_limit: int | None = None,
) -> dict:
    """Persist a credit card application and applicant to the database.

    Call this after apply_for_card returns a decision.

    Args:
        card_id: The ID of the credit card product.
        first_name: Applicant's first name.
        last_name: Applicant's last name.
        email: Applicant's email address.
        annual_income: Applicant's annual income in dollars.
        credit_score: Applicant's credit score (300–850).
        decision: The decision from apply_for_card ("approved" or "declined").
        approved_limit: The approved credit limit (if approved).

    Returns:
        A dict confirming the saved application ID.
    """
    conn = _get_connection()
    try:
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

        return {
            "application_id": cur.lastrowid,
            "status": status,
            "message": "Application saved successfully.",
        }
    finally:
        conn.close()


if __name__ == "__main__":
    mcp.run(transport="stdio")
