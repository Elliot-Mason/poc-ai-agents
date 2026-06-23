import os
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).parent

# Load .env file from the project root.
_env_path = PROJECT_ROOT / ".env"
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

from chat.agent import CreditCardAgent
from llm.bedrock_adapter import BedrockAdapter

DB_PATH = PROJECT_ROOT / "db" / "creditcards.db"
FRONTEND_DIR = PROJECT_ROOT / "frontend"

agent: CreditCardAgent | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global agent
    llm = BedrockAdapter(
        model_id=os.getenv("BEDROCK_MODEL_ID", "global.anthropic.claude-sonnet-4-5-20250929-v1:0"),
        region=os.getenv("AWS_REGION", "ap-southeast-2"),
    )
    agent = CreditCardAgent(llm)
    await agent.start()
    print("CreditCardBot agent started")
    yield
    await agent.stop()


app = FastAPI(title="CreditCardBot API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]


class ChatResponse(BaseModel):
    reply: str


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    if not req.messages:
        raise HTTPException(status_code=400, detail="messages must not be empty.")
    if req.messages[-1].role != "user":
        raise HTTPException(status_code=400, detail="last message must be from the user.")

    history = [m.model_dump() for m in req.messages[:-1]]
    user_message = req.messages[-1].content

    try:
        reply = await agent.chat(user_message, history=history)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM request failed: {e}")

    return ChatResponse(reply=reply)


@app.get("/applications")
async def list_applications():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("""
            SELECT
                a.id,
                ap.first_name,
                ap.last_name,
                ap.email,
                ap.credit_score,
                ap.annual_income,
                cc.card_name,
                a.status,
                a.approved_limit,
                a.created_at
            FROM applications a
            JOIN applicants ap ON a.applicant_id = ap.id
            JOIN credit_cards cc ON a.card_id = cc.id
            ORDER BY a.created_at DESC
        """).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# Serve frontend static files (must be after API routes)
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
