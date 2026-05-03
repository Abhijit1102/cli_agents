# CLI Agents

A Python CLI agent that wraps an OpenAI-powered assistant with local tool execution and project-aware memory.

## Overview

`cli_agents` is a terminal application that lets you interact with an AI agent using natural language. It supports:

- file operations (`read_file`, `write_file`, `list_folder`, `search_project`)
- image analysis for local files (`analyze_image`)
- shell command execution (`run_shell_command`)
- external knowledge lookup via Tavily (`tavily_search`)
- conversational memory and usage tracking
- a trusted folder prompt before enabling file and shell access

## Project Structure

- `cli_agents/main.py` — Typer-based CLI entrypoint and application startup.
- `cli_agents/config/settings.py` — environment loading and application configuration.
- `cli_agents/core/agent.py` — AI controller that manages LLM calls and tool execution.
- `cli_agents/ui/app.py` — Rich-powered terminal UI and command loop.
- `cli_agents/memory/history.py` — conversation history and message assembly.
- `cli_agents/tools/` — tool definitions for project inspection and shell execution.

## Requirements

- Python 3.12+
- `anyio`
- `openai`
- `python-dotenv`
- `Pillow`
- `rich`
- `typer`
- `tavily-python`

Optional:

- `uv` for package installation and environment setup

## Setup

1. Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your_openai_api_key
OPENAI_BASE_URL=https://api.openai.com/v1
TAVILY_API_KEY=your_tavily_api_key
MODEL=openai/gpt-4o-mini
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

If you prefer `uv`, install it and use it to install the project dependencies:

```bash
pip install uv
uv install
```

> If there is no `requirements.txt`, install from `pyproject.toml`:

```bash
pip install .
```

## Run

Start the CLI agent with:

```bash
python -m cli_agents.main start
```

Or if the package is installed as a script:

```bash
cli_agents start
```

## Available Commands

Inside the CLI session, use:

- `/help` — show built-in commands
- `/reset` — reset conversation history
- `/usage` — show the last LLM usage stats
- `/cwd` — print current working directory
- `/clear` — clear the screen
- `/theme` — list available themes
- `/theme <name>` — switch active theme instantly, e.g. `/theme purple`
- `exit` / `quit` — exit the session

## Security

On startup, the app prompts "Trust this folder and enable file/shell access?". If you decline, the agent exits immediately.

## License

MIT License

MIT License © 2024

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
out of or in connection with the Software or the use or other dealings in the
Software.