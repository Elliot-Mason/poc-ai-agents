import json
import os
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

# Load .env file
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

DB_PATH = Path(__file__).parent / "mortgage.db"
PROMPT_LOG = Path(__file__).parent / "prompts.log"

import traceback

from chat.agent import MortgageAgent
from llm.bedrock_adapter import BedrockAdapter

agent: MortgageAgent | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global agent
    try:
        llm = BedrockAdapter(
            model_id=os.getenv("BEDROCK_MODEL_ID", "global.anthropic.claude-sonnet-4-5-20250929-v1:0"),
            region=os.getenv("AWS_REGION", "ap-southeast-2"),
        )
        agent = MortgageAgent(llm)
        await agent.start()
        print("Mortgage agent started")
    except Exception as e:
        print("LIFESPAN STARTUP EXCEPTION DETECTED:")
        traceback.print_exc()
        raise e
    yield
    try:
        if agent:
            await agent.stop()
    except Exception as e:
        print("LIFESPAN SHUTDOWN EXCEPTION DETECTED:")
        traceback.print_exc()



from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.post("/api/chat")
async def chat(request: Request):
    body = await request.json()
    # Robust key resolution to support multiple testing platform formats
    message = None
    history = body.get("history", [])

    if "message" in body:
        message = body["message"]
    elif "prompt" in body:
        message = body["prompt"]
    elif "text" in body:
        message = body["text"]
    elif "messages" in body and isinstance(body["messages"], list) and len(body["messages"]) > 0:
        last_msg = body["messages"][-1]
        if isinstance(last_msg, dict):
            message = last_msg.get("content", last_msg.get("text", ""))
        else:
            message = str(last_msg)

        # Extract history from preceding messages if not already provided
        if not history:
            history = []
            for m in body["messages"][:-1]:
                if isinstance(m, dict):
                    role = m.get("role", "user")
                    content = m.get("content", m.get("text", ""))
                    history.append({"role": role, "content": content})

    if message is None:
        message = ""
    stream = body.get("stream", True)

    with open(PROMPT_LOG, "a") as f:
        f.write(f"[{datetime.now(timezone.utc).isoformat()}] {message}\n")

    if stream:
        async def event_stream():
            async for token in agent.stream_chat(message, history=history):
                yield f"data: {json.dumps({'token': token})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    tokens = []
    async for token in agent.stream_chat(message, history=history):
        tokens.append(token)
    response_text = "".join(tokens)
    return {
        "response": response_text,
        "message": response_text,
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": response_text
                }
            }
        ]
    }


@app.get("/api/rates")
async def get_rates():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("SELECT * FROM rates ORDER BY loan_type, rate").fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


@app.get("/api/quotes")
async def get_quotes():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("SELECT * FROM quotes ORDER BY created_at DESC").fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


app.mount("/", StaticFiles(directory="static", html=True), name="static")
