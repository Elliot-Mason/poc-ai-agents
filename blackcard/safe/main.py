import json
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

app = FastAPI()

RESPONSE_TEXT = "I'm not at liberty to talk about anything"


@app.post("/api/chat")
async def chat(request: Request):
    body = await request.json()
    message = body["message"]
    body.get("history", [])
    stream = body.get("stream", True)

    with open("assessments.txt", "a") as f:
        f.write(f"[{datetime.now(timezone.utc).isoformat()}] {message}\n")

    if stream:
        async def event_stream():
            for token in RESPONSE_TEXT:
                yield f"data: {json.dumps({'token': token})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    return {"response": RESPONSE_TEXT}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
