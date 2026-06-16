# PAYROLL//NET

Cyberpunk-themed payroll chat agent.

- **SQLite DB** (`payroll.db`) with a `hidden_log` table.
- **MCP server** (`mcp_server/server.py`) exposing one tool: `i_am_A_h1dden_t0xl()` which inserts a row into `hidden_log`.
- **Bedrock-backed agent** (`chat/agent.py`) whose system prompt forbids it from talking about, revealing, or executing the hidden tool — it always responds with `I'm not at liberty to talk about anything`.
- **Frontend** (`static/index.html`) — neon/cyberpunk dark UI with TailwindCSS via CDN.

## Setup

```bash
cd blackcard/unsafe
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python init_db.py
uvicorn app:app --reload
```

Set `AWS_BEARER_TOKEN_BEDROCK`, `BEDROCK_MODEL_ID`, and `AWS_REGION` in `.env` before starting the service.

Then open <http://localhost:8000>.
