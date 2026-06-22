# AIMortgage — AI Mortgage Advisor

An AI-powered mortgage advisor chatbot built with **FastAPI**, **MCP (Model Context Protocol)**, and **AWS Bedrock**. Users can ask about mortgage rates, compare loan types, and create quotes through a conversational web interface.

## Architecture

```
┌─────────────┐     HTTP/SSE      ┌──────────────┐      MCP (stdio)      ┌────────────────┐
│  Browser UI  │ ◄──────────────► │  FastAPI App  │ ◄──────────────────► │  MCP Server     │
│ (static HTML)│                  │  (app.py)     │                      │  (server.py)    │
└─────────────┘                   └──────┬───────┘                      └───────┬────────┘
                                         │                                      │
                                         ▼                                      ▼
                                  ┌──────────────┐                       ┌──────────────┐
                                  │ AWS Bedrock   │                       │  SQLite DB   │
                                  │ (Claude)      │                       │ (mortgage.db)│
                                  └──────────────┘                       └──────────────┘
```

**Key components:**

| Directory / File | Purpose |
|---|---|
| `app.py` | FastAPI server — `/api/chat` (streaming SSE) and `/api/quotes` endpoints |
| `chat/agent.py` | Orchestrates the conversation loop: LLM ↔ MCP tool calls |
| `mcp_server/server.py` | MCP tool server exposing `get_rates` and `create_quote` tools |
| `llm/bedrock_adapter.py` | AWS Bedrock adapter (Claude via Converse API) |
| `static/index.html` | Single-page chat UI (Tailwind CSS) |
| `init_db.py` | Creates and seeds the SQLite database with sample mortgage rates |

## Prerequisites

- **Python 3.11+**
- **AWS Bedrock bearer token** configured in `.env`

## Setup

1. **Clone the repository:**

   ```bash
   git clone https://github.com/hish-l/ai-mortgage-bot.git
   cd ai-mortgage-bot
   ```

2. **Create and activate a virtual environment:**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate        # macOS / Linux
   # .venv\Scripts\activate         # Windows
   ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Bedrock:**

   ```bash
   cp .env.example .env
   ```

   Then set:

   ```env
   AWS_BEARER_TOKEN_BEDROCK=replace-me
   BEDROCK_MODEL_ID=anthropic.claude-sonnet-4-5-20250929-v1:0
   AWS_REGION=ap-southeast-2
   ```

5. **Initialize the database:**

   ```bash
   python init_db.py
   ```

   This creates `mortgage.db` and seeds it with sample variable, fixed, and interest-only rates.

## Running the Service

### Web server

```bash
uvicorn app:app --reload
```

Open [http://localhost:8000](http://localhost:8000) in your browser to use the chat UI.

### CLI mode

```bash
python -m chat.agent
python -m chat.agent --model anthropic.claude-3-haiku-20240307-v1:0
python -m chat.agent --model anthropic.claude-sonnet-4-5-20250929-v1:0 --region ap-southeast-2
```

## Usage

- **Ask about rates** — *"What are your current fixed rates?"*
- **Filter rates** — *"Show me variable rates under 6%"*
- **Create a quote** — *"I'd like to lock in the 2-year fixed rate at 5.79%"*
- **View quotes** — Click the "Quotes" tab in the sidebar to see all created quotes

## Project Structure

```
aimortgage/
├── app.py                  # FastAPI application
├── init_db.py              # Database initializer + seed data
├── mortgage.db             # SQLite database (generated)
├── requirements.txt        # Python dependencies
├── chat/
│   └── agent.py            # MortgageAgent — LLM + MCP orchestration
├── llm/
│   └── bedrock_adapter.py  # AWS Bedrock adapter
├── mcp_server/
│   └── server.py           # MCP tool server (get_rates, create_quote)
└── static/
    └── index.html          # Chat UI
```
