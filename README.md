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
- `exit` / `quit` — exit the session

## Security

On startup, the app prompts "Trust this folder and enable file/shell access?". If you decline, the agent exits immediately.

## Notes

- `OPENAI_API_KEY` is required.
- `OPENAI_BASE_URL` is optional; omit it for the default OpenAI endpoint.
- `TAVILY_API_KEY` is optional, but required for Tavily-based searches.
- Default model is `openai/gpt-4o-mini` unless overridden by the `MODEL` environment variable.

## Contributing

Contributions are welcome. Open an issue or submit a pull request for improvements, bug fixes, or new tool integrations.
