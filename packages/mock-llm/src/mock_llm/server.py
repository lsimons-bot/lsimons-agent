"""Mock LLM server that returns canned responses."""

import json
import uuid
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

# Load scenarios from file
SCENARIOS_PATH = Path(__file__).parent.parent.parent / "scenarios.json"
with open(SCENARIOS_PATH) as f:
    SCENARIOS_DATA = json.load(f)

# Track conversation state: session_id -> (scenario_name, step_index)
conversation_state: dict[str, tuple[str, int]] = {}


class Message(BaseModel):
    role: str
    content: str | None = None
    tool_calls: list | None = None
    tool_call_id: str | None = None


class ChatRequest(BaseModel):
    model: str
    messages: list[Message]
    tools: list | None = None
    max_tokens: int | None = None


def find_scenario(user_message: str) -> dict | None:
    """Find a scenario matching the user message."""
    user_lower = user_message.lower()
    for scenario in SCENARIOS_DATA["scenarios"]:
        if scenario["trigger"] in user_lower:
            return scenario
    return None


def get_session_id(messages: list[Message]) -> str:
    """Generate a session ID from the conversation."""
    # Use hash of first user message as session identifier
    for msg in messages:
        if msg.role == "user" and msg.content:
            return str(hash(msg.content))
    return "default"


def build_response(content: str | None, tool_calls: list | None = None) -> dict:
    """Build OpenAI-format response."""
    message = {"role": "assistant", "content": content}
    if tool_calls:
        message["tool_calls"] = tool_calls

    return {
        "id": f"mock-{uuid.uuid4().hex[:8]}",
        "object": "chat.completion",
        "model": "mock-model",
        "choices": [
            {
                "index": 0,
                "message": message,
                "finish_reason": "tool_calls" if tool_calls else "stop",
            }
        ],
    }


@app.post("/chat/completions")
def chat_completions(request: ChatRequest):
    """Handle chat completion requests."""
    # Get last user message
    last_user_message = ""
    for msg in reversed(request.messages):
        if msg.role == "user" and msg.content:
            last_user_message = msg.content
            break

    # Check if this is a tool result (continuation of scenario)
    has_tool_result = any(msg.role == "tool" for msg in request.messages)

    session_id = get_session_id(request.messages)

    if has_tool_result and session_id in conversation_state:
        # Continue existing scenario
        scenario_name, step_index = conversation_state[session_id]
        for scenario in SCENARIOS_DATA["scenarios"]:
            if scenario["name"] == scenario_name:
                next_step = step_index + 1
                if next_step < len(scenario["steps"]):
                    conversation_state[session_id] = (scenario_name, next_step)
                    step_response = scenario["steps"][next_step]["response"]
                    return build_response(
                        step_response.get("content"),
                        step_response.get("tool_calls"),
                    )
                else:
                    # Scenario complete
                    del conversation_state[session_id]
                    return build_response("Scenario complete.")

    # Find matching scenario
    scenario = find_scenario(last_user_message)
    if scenario:
        conversation_state[session_id] = (scenario["name"], 0)
        step_response = scenario["steps"][0]["response"]
        return build_response(
            step_response.get("content"),
            step_response.get("tool_calls"),
        )

    # Default response
    return build_response(SCENARIOS_DATA["default_response"]["content"])


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}


def main():
    """Run the mock server."""
    import uvicorn

    print("Starting mock LLM server on http://localhost:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
