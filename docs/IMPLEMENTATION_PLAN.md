# Implementation Plan

## Overview

Build a minimal coding agent in small increments. Each phase produces something runnable and testable.

## Phase 1: Hello World CLI

**Goal:** Runnable CLI that prints a message.

Tasks:
1. Create root `pyproject.toml` with uv workspace
2. Create `packages/core/pyproject.toml` with CLI entry point
3. Create `packages/core/src/lsimons_agent/cli.py` - just prints hello
4. Add `.gitignore`

**Done when:** `uv run lsimons-agent` prints hello.

## Phase 2: Mock LLM Server

**Goal:** Predictable test server that mimics the LiteLLM API.

Tasks:
1. Create `packages/mock-llm/` with FastAPI server
2. Implement `POST /chat/completions` endpoint (OpenAI format)
3. Match incoming prompts to canned responses from a scenarios file
4. Create "hello world" scenario: agent asked to write hello.py, responds with tool calls

**Done when:** `curl` to mock server returns expected canned response.

## Phase 3: Single LLM Call

**Goal:** CLI sends one hardcoded message to LLM and prints response.

Tasks:
1. Create `llm.py` with `chat(messages)` function
2. Call LLM from cli.py with a test message
3. Print the response

**Done when:** Running CLI against mock server prints canned response.

## Phase 4: Conversation Loop

**Goal:** Interactive REPL with multi-turn conversation.

Tasks:
1. Create `agent.py` with input loop
2. Maintain messages list across turns
3. Add `/clear` and Ctrl+C handling

**Done when:** Can have back-and-forth conversation with mock server.

## Phase 5: Tools

**Goal:** Agent can read/write files and run commands.

Tasks:
1. Create `tools.py` with read_file, write_file, edit_file, bash
2. Add tool definitions to LLM calls
3. Parse tool_calls from response, execute, return results
4. Loop until no more tool calls

**Done when:** Run "hello world" scenario against mock server, agent creates working hello.py.

## Phase 6: Web Interface

**Goal:** Browser-based chat UI.

Tasks:
1. Create `packages/web/` with FastAPI server
2. Create Jinja2 + HTMX templates
3. SSE streaming for responses
4. Extract shared agent logic from CLI

**Done when:** Can chat at localhost:8765.

## Phase 7: Electron App

**Goal:** Desktop wrapper.

Tasks:
1. Create `packages/electron/` with main.js
2. Spawn web server, open BrowserWindow
3. Clean shutdown

**Done when:** Desktop app works.

## Future Ideas (Not In Scope)

- Conversation persistence
- Syntax highlighting
- Token usage display
