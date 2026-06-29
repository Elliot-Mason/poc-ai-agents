import json
import traceback
from datetime import datetime, timezone
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

RESPONSE_TEXT = "I'm not at liberty to talk about anything"


@app.post("/api/chat")
async def chat(request: Request):
    try:
        body = await request.json()
        message = None
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

        if message is None:
            message = ""

        stream = body.get("stream", False)

        with open("assessments.txt", "a") as f:
            f.write(f"[{datetime.now(timezone.utc).isoformat()}] {message}\n")

        if stream:
            async def event_stream():
                for token in RESPONSE_TEXT:
                    yield f"data: {json.dumps({'token': token})}\n\n"
                yield f"data: {json.dumps({'done': True})}\n\n"
            return StreamingResponse(event_stream(), media_type="text/event-stream")

        return {
            "response": RESPONSE_TEXT,
            "message": RESPONSE_TEXT,
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": RESPONSE_TEXT
                    }
                }
            ]
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
