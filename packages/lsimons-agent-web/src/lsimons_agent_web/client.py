"""CLI client that connects to lsimons-agent-web server."""

import json
import sys
from typing import Any

import httpx

# ANSI color codes
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
MAGENTA = "\033[35m"
RED = "\033[31m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

ASCII_ART = f"""{CYAN}{BOLD}
    ┌───────────┐
    │  ◉    ◉  │
    │    ──    │
    │  ╲____╱  │
    └─────┬────┘
          │
    ╔═════╧═════╗
    ║  Leo-Bot  ║
    ╚═══════════╝{RESET}
"""


def run() -> None:
    """Run the CLI client that connects to the web server."""
    base_url = "http://localhost:8765"

    print(ASCII_ART)
    print(f"{BOLD}{MAGENTA}lsimons-agent{RESET}")
    print(f"{DIM}{'─' * 40}{RESET}")
    print(f"{DIM}Type a message, /clear to reset, Ctrl+C to exit{RESET}")
    print()

    while True:
        try:
            user_input = input(f"{BOLD}{GREEN}You:{RESET} ").strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n{DIM}Bye!{RESET}")
            break

        if not user_input:
            continue

        if user_input == "/clear":
            try:
                httpx.post(f"{base_url}/clear", timeout=10.0)
                print(f"{DIM}Cleared.{RESET}")
            except httpx.RequestError as e:
                print(f"{RED}Error: {e}{RESET}")
            continue

        try:
            _send_message(base_url, user_input)
        except httpx.RequestError as e:
            print(f"{RED}Error: {e}{RESET}")


def _send_message(base_url: str, message: str) -> None:
    """Send a message and stream the response."""
    with httpx.stream(
        "POST",
        f"{base_url}/chat",
        json={"message": message},
        timeout=300.0,
    ) as response:
        response.raise_for_status()

        event_type: str | None = None
        current_text = ""

        for line in response.iter_lines():
            if line.startswith("event: "):
                event_type = line[7:]
            elif line.startswith("data: "):
                data: dict[str, Any] = json.loads(line[6:])
                _handle_event(event_type, data, current_text)
                if event_type == "text":
                    if not current_text:
                        current_text = str(data.get("content", ""))
                    else:
                        current_text += str(data.get("content", ""))
                elif event_type in ("tool", "done"):
                    current_text = ""


def _handle_event(event_type: str | None, data: dict[str, Any], current_text: str) -> None:
    """Handle a single SSE event."""
    if event_type == "text":
        content = str(data.get("content", ""))
        if not current_text:
            # First text chunk - print prefix
            sys.stdout.write(f"\n{BOLD}{CYAN}Agent:{RESET} {content}")
        else:
            sys.stdout.write(content)
        sys.stdout.flush()
    elif event_type == "tool":
        name = str(data.get("name", ""))
        args: dict[str, Any] = data.get("args", {})
        print(f"\n{YELLOW}[Tool: {name}({format_args(args)})]{RESET}")
    elif event_type == "done":
        print("\n")


def format_args(args: dict[str, Any]) -> str:
    """Format tool arguments for display."""
    parts: list[str] = []
    for k, v in args.items():
        if isinstance(v, str) and len(v) > 30:
            v = v[:30] + "..."
        parts.append(f"{k}={v!r}")
    return ", ".join(parts)


if __name__ == "__main__":
    run()
