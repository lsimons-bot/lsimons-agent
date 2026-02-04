"""Web server for lsimons-agent."""

import asyncio
import json
import sys
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from lsimons_agent.agent import new_conversation, process_message

from .terminal import Terminal

app = FastAPI()

# Single-user terminal sessions
terminal_agent: Terminal | None = None
terminal_shell: Terminal | None = None


def get_resource_path(relative_path: str) -> Path:
    """Get path to resource, handling PyInstaller bundled mode."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        # Running in PyInstaller bundle
        return Path(sys._MEIPASS) / relative_path
    # Running in normal Python environment
    return Path(__file__).parent.parent.parent / relative_path


TEMPLATES_DIR = get_resource_path("templates")
STATIC_DIR = get_resource_path("static")

# Single-user conversation state
messages = new_conversation()


def event_stream(user_message: str):
    """Generate SSE events for a chat response."""
    for event_type, data in process_message(messages, user_message):
        if event_type == "text":
            yield f"event: text\ndata: {json.dumps({'content': data})}\n\n"
        elif event_type == "tool":
            yield f"event: tool\ndata: {json.dumps(data)}\n\n"
        elif event_type == "done":
            yield "event: done\ndata: {}\n\n"


@app.get("/", response_class=HTMLResponse)
def index():
    """Serve the chat page."""
    return (TEMPLATES_DIR / "index.html").read_text()


@app.get("/favicon.ico")
def favicon():
    """Serve the favicon."""
    return FileResponse(STATIC_DIR / "favicon.ico", media_type="image/x-icon")


@app.get("/logo.png")
def logo():
    """Serve the logo."""
    return FileResponse(STATIC_DIR / "logo.png", media_type="image/png")


@app.post("/chat")
def chat_endpoint(request: dict):
    """Handle chat messages and return SSE stream."""
    return StreamingResponse(
        event_stream(request.get("message", "")),
        media_type="text/event-stream",
    )


@app.post("/clear")
def clear():
    """Clear conversation history."""
    global messages
    messages = new_conversation()
    return {"status": "ok"}


@app.get("/terminal", response_class=HTMLResponse)
def terminal_page():
    """Serve the terminal page."""
    return (TEMPLATES_DIR / "terminal.html").read_text()


async def _handle_terminal_websocket(
    websocket: WebSocket, terminal: Terminal
) -> None:
    """Handle WebSocket I/O for a terminal."""
    try:
        while True:
            # Check if terminal is still running
            if not terminal.is_running():
                break

            # Poll for terminal output
            while True:
                data = terminal.read_nowait()
                if data is None:
                    break
                try:
                    await websocket.send_bytes(data)
                except RuntimeError:
                    # WebSocket already closed
                    return

            # Check for websocket input (with timeout)
            try:
                message = await asyncio.wait_for(
                    websocket.receive(), timeout=0.05
                )
                if message.get("type") == "websocket.disconnect":
                    break
                if "bytes" in message:
                    terminal.write(message["bytes"])
                elif "text" in message:
                    # Handle JSON commands (resize)
                    try:
                        cmd = json.loads(message["text"])
                        if cmd.get("type") == "resize":
                            terminal.resize(cmd["rows"], cmd["cols"])
                    except json.JSONDecodeError:
                        # Plain text input
                        terminal.write(message["text"].encode())
            except asyncio.TimeoutError:
                pass

    except (WebSocketDisconnect, RuntimeError):
        # WebSocket disconnected
        pass


@app.websocket("/ws/terminal/agent")
async def terminal_agent_websocket(websocket: WebSocket):
    """WebSocket endpoint for agent terminal."""
    global terminal_agent

    await websocket.accept()

    # Clean up dead terminal
    if terminal_agent is not None and not terminal_agent.is_running():
        terminal_agent.stop()
        terminal_agent = None

    # Start new terminal or reconnect to existing
    if terminal_agent is None:
        terminal_agent = Terminal(command=["lsimons-agent-client"])
        terminal_agent.start()
    else:
        # Reconnecting - replay scrollback buffer
        scrollback = terminal_agent.get_scrollback()
        if scrollback:
            await websocket.send_bytes(scrollback)

    await _handle_terminal_websocket(websocket, terminal_agent)


@app.websocket("/ws/terminal/shell")
async def terminal_shell_websocket(websocket: WebSocket):
    """WebSocket endpoint for shell terminal."""
    global terminal_shell

    await websocket.accept()

    # Clean up dead terminal
    if terminal_shell is not None and not terminal_shell.is_running():
        terminal_shell.stop()
        terminal_shell = None

    # Start new terminal or reconnect to existing
    if terminal_shell is None:
        terminal_shell = Terminal()
        terminal_shell.start()
    else:
        # Reconnecting - replay scrollback buffer
        scrollback = terminal_shell.get_scrollback()
        if scrollback:
            await websocket.send_bytes(scrollback)

    await _handle_terminal_websocket(websocket, terminal_shell)


@app.post("/terminal/stop")
def terminal_stop():
    """Stop all terminal sessions."""
    global terminal_agent, terminal_shell
    if terminal_agent is not None:
        terminal_agent.stop()
        terminal_agent = None
    if terminal_shell is not None:
        terminal_shell.stop()
        terminal_shell = None
    return {"status": "ok"}


def main():
    """Run the web server."""
    import uvicorn

    print("Starting web server on http://localhost:8765")
    uvicorn.run(app, host="127.0.0.1", port=8765)


if __name__ == "__main__":
    main()
