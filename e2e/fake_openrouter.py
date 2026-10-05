"""A stand-in for OpenRouter, for the browser tests. It never calls the internet.

It answers each feature with a fixed reply, chosen from the words in the prompt.
"""

import asyncio
import json

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

app = FastAPI()

SUMMARY = (
    "Two projects must fix their data before the next stage. "
    "Most others can go ahead with actions. Three projects have no answers yet."
)
INTERVIEW = {
    "answer": "Yes",
    "evidence": "The expected output is a weekly forecast.",
    "followUp": "",
}
EVIDENCE = [{"id": "3.1", "answer": "Partly", "evidence": "Sales data exists but is not cleaned."}]
BRIEF = {
    "headline": "The test project can go ahead once the data is cleaned.",
    "summary": "The expected output is clear. The data exists but is not ready yet.",
    "actions": [{"question": "3.1", "action": "Clean the sales data.", "owner": "Data team"}],
    "risks": ["The pilot starts before the data is ready."],
}
USAGE = {"prompt_tokens": 100, "completion_tokens": 50, "cost": 0.0001}


def reply(content: object) -> JSONResponse:
    message = {"content": json.dumps(content)}
    return JSONResponse({"choices": [{"message": message}], "usage": USAGE})


@app.post("/api/v1/chat/completions")
async def chat(request: Request):
    body = await request.json()
    prompt = body["messages"][0]["content"]
    if body.get("stream"):

        async def pieces():
            for word in SUMMARY.split(" "):
                yield f"data: {json.dumps({'choices': [{'delta': {'content': word + ' '}}]})}\n\n"
                await asyncio.sleep(0.02)
            yield f"data: {json.dumps({'choices': [], 'usage': USAGE})}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(pieces(), media_type="text/event-stream")
    if '"followUp"' in prompt:
        return reply(INTERVIEW)
    if "JSON array" in prompt:
        return reply(EVIDENCE)
    return reply(BRIEF)
