"""Agent loop for interactive conversation."""

import json
import os
from collections.abc import Generator
from typing import Any

from lsimons_agent.tools import TOOLS, bash, execute

# Use lsimons-llm when LLM_API_KEY is set, otherwise use local mock-compatible client
if os.environ.get("LLM_API_KEY"):
    from lsimons_llm import LLMClient, load_config  # type: ignore[import-untyped]

    _config: Any = load_config()  # type: ignore[reportUnknownVariableType]
    _client: Any = LLMClient(_config)  # type: ignore[reportUnknownVariableType]

    def chat(
        messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        """Send messages to LLM and return raw API response dict."""
        result: dict[str, Any] = _client.chat_raw(messages, tools)  # type: ignore[no-any-return]
        return result
else:
    from lsimons_agent.llm import chat  # noqa: F401


SYSTEM_PROMPT = """\
You are a coding assistant. You help the user by reading, writing, and editing \
files, and running shell commands.

When editing files, use edit_file with the exact string to replace - include \
enough context to make the match unique.

Be concise. Execute tasks directly without asking for confirmation."""

Event = tuple[str, Any]


def process_message(messages: list[dict[str, Any]], user_message: str) -> Generator[Event]:
    """
    Process a user message and yield events.

    Yields tuples of (event_type, data):
    - ("text", content) - Agent text response
    - ("tool", {"name": name, "args": args}) - Tool being executed
    - ("done", None) - Processing complete

    Modifies messages list in place.
    """
    messages.append({"role": "user", "content": user_message})

    while True:
        response = chat(messages, tools=TOOLS)
        message: dict[str, Any] = response["choices"][0]["message"]
        content: str = message.get("content", "")
        tool_calls: list[dict[str, Any]] = message.get("tool_calls", [])

        if content:
            yield ("text", content)

        if not tool_calls:
            messages.append(message)
            break

        messages.append(message)
        for tool_call in tool_calls:
            fn: dict[str, Any] = tool_call["function"]
            name: str = fn["name"]
            args: dict[str, str] = json.loads(fn["arguments"])

            yield ("tool", {"name": name, "args": args})

            try:
                result = execute(name, args)
            except Exception as e:
                result = f"Error: {e}"

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": result,
                }
            )

    yield ("done", None)


def new_conversation() -> list[dict[str, Any]]:
    """Create a new conversation with system prompt."""
    return [{"role": "system", "content": SYSTEM_PROMPT}]


def run() -> None:
    """Run the interactive CLI agent loop."""
    messages = new_conversation()

    print("lsimons-agent")
    print("-" * 40)
    print("Type a message, /clear to reset, !cmd for bash, Ctrl+C to exit")
    print()

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nBye!")
            break

        if not user_input:
            continue

        if user_input == "/clear":
            messages = new_conversation()
            print("Cleared.")
            continue

        if user_input.startswith("!"):
            print(bash(user_input[1:]))
            continue

        for event_type, data in process_message(messages, user_input):
            if event_type == "text":
                print(f"\nAgent: {data}")
            elif event_type == "tool":
                print(f"[Tool: {data['name']}({format_args(data['args'])})]")
            elif event_type == "done":
                print()


def format_args(args: dict[str, Any]) -> str:
    """Format tool arguments for display."""
    parts: list[str] = []
    for k, v in args.items():
        if isinstance(v, str) and len(v) > 30:
            v = v[:30] + "..."
        parts.append(f"{k}={v!r}")
    return ", ".join(parts)
