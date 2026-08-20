# CLI Agents

`cli_agents` is an interactive Python terminal agent for exploring and working on a real project. It sends conversation history to an OpenAI-compatible chat API and gives the model local filesystem tools, shell execution, image analysis, and optional tools supplied by MCP servers.

## What It Does

- Rich terminal interface with live timestamps, status panels, Markdown, and tool progress
- Short-term conversation memory for the current session
- Project-aware system prompt containing the project root, filtered file tree, and optional instructions
- Local tools for reading, writing, listing, searching, image analysis, shell commands, and diffs
- Optional MCP integration over stdio, SSE, or streamable HTTP
- Startup folder-trust prompt
- Fuzzy slash-command palette that adapts to terminal size

Conversation history is not persisted to disk. `/history` shows only prompts from the current process.

## Requirements and Install

- Python 3.12 or newer
- An OpenAI API key, or an OpenAI-compatible provider key
- Dependencies from `requirements.txt` or `pyproject.toml`

```powershell
pip install -r requirements.txt
```

Or install the package and its dependencies:

```powershell
pip install .
```

The package also defines the `cli_agents` command. `uv` can be used instead of `pip`.

## Configuration

Configuration is read from the project root passed to `start`, or from the current directory when no path is supplied. Create a `.cli_agents` directory in that project.

### `.cli_agents/env.json`

This file must contain JSON, not dotenv syntax:

```json
{
  "OPENAI_API_KEY": "your-api-key",
  "OPENAI_BASE_URL": "https://api.openai.com/v1",
  "MODEL": "gpt-4o-mini"
}
```

Environment variables are also accepted. Values from `env.json` are added only when the environment does not already define them.

| Setting | Required | Purpose |
| --- | --- | --- |
| `OPENAI_API_KEY` | Yes | Main chat API credential |
| `OPENAI_BASE_URL` | No | OpenAI-compatible API endpoint |
| `MODEL` | No | Chat model; defaults to `openai/gpt-4o-mini` |

### Other project files

- `.cli_agents/settings.json`: JSON settings; general values take precedence over environment variables.
- `.cli_agents/CLI_AGENT.md`: project-specific instructions inserted into the system prompt.
- `.cli_agents/mcp.config.json`: enables MCP only when this exact file exists.

Example MCP configuration:

```json
{
  "mcpServers": {
    "local-tools": {
      "command": "python",
      "args": ["path/to/server.py"]
    },
    "remote-tools": {
      "transport": "sse",
      "url": "https://example.com/mcp",
      "headers": {"Authorization": "Bearer your-token"}
    },
    "http-tools": {
      "transport": "streamable-http",
      "url": "https://example.com/mcp",
      "api_key": "your-token"
    }
  }
}
```

MCP servers are initialized at startup, retried up to three times, and disconnected when the session ends. MCP tools are exposed as `server_name__tool_name`. Connection initialization has a 15-second timeout and tool calls have a 60-second timeout.

## Start

Run against the current directory:

```powershell
python -m cli_agents.main start
```

Run against another project:

```powershell
python -m cli_agents.main start C:\path\to\project
```

Startup resolves the project, asks for folder trust, loads configuration, builds the project-aware prompt, creates the OpenAI client, connects MCP servers, and starts the interactive UI. Answering `n` to the trust prompt exits immediately.

## Slash Commands

Type `/` to open the fuzzy command palette. Use arrow keys and Enter to select a command.

| Command | Purpose |
| --- | --- |
| `/help` | Show the command registry |
| `/reset` | Clear conversation memory and usage data |
| `/usage` | Show the latest API usage object |
| `/cwd` | Show the process working directory |
| `/history` | Replay prompts from this session |
| `/clear` | Clear and redraw the terminal |
| `/clock` | Show a five-second live clock |
| `/mcp` | Show connected MCP servers |
| `/config` | Show model, base URL, and MCP status |
| `/theme` | List available themes |
| `/theme <name>` | Switch to `cyan`, `green`, `purple`, `yellow`, `orange`, `pink`, or `white` |
| `/init_project` | Scan the project and write `.cli_agents/PROJECT_DESCRIPTION.md` |
| `/sandbox ...` | Registered, but its handler is not currently included in the UI module |
| `exit`, `quit` | Shut down MCP connections and exit |

## Built-in Tools

The model chooses these tools during a normal message. `AIController` executes them and appends each result to the conversation.

| Tool | Behavior |
| --- | --- |
| `read_file(path)` | Reads a UTF-8 text file |
| `write_file(path, content)` | Creates parent folders and creates or overwrites a UTF-8 file |
| `list_folder(path)` | Lists files and directories, with folders first |
| `search_project(query, root)` | Searches supported text files recursively and returns paths and excerpts |
| `analyze_image(path)` | Sends PNG, JPEG, GIF, or WebP data to `gpt-4o-mini` for analysis |
| `run_shell_command(command, cwd, timeout)` | Runs a platform shell command with a 30-second default timeout |
| `git_diff(old_code, new_code, file_path)` | Produces JSON containing a unified diff and line counts |

The agent allows up to four model/tool reasoning rounds per message. Empty input is ignored, and `/reset` is handled without an API call.

## Source Layout

```text
cli_agents/
├── main.py                 Typer entry point and application wiring
├── utils.py                Ignore rules, project tree, and project-description generation
├── config/                 AppConfig and process-wide configuration
├── core/                   Agent loop, system prompt, and MCP gateway
├── memory/history.py       In-memory OpenAI message history
├── tools/                  Filesystem, shell, and diff tools
└── ui/                     Rich UI, trust prompt, palette, themes, and renderers
```

Important modules:

- `main.py` wires configuration, client, memory, agent, and UI together.
- `core/agent.py` performs model calls, routes local/MCP tools, records usage, and shuts down MCP.
- `core/prompt.py` builds the system prompt from the project tree and `CLI_AGENT.md`.
- `memory/history.py` preserves system, user, assistant, and tool messages in OpenAI format.
- `tools/__init__.py` registers tool schemas and dispatches tool functions.
- `ui/app.py` handles commands, live status, responses, diffs, and cleanup.

## Request Flow

```text
User input
  -> ChatUI command handling
  -> AIController.handle_message()
  -> ConversationMemory + OpenAI chat.completions
  -> optional local or MCP tool call
  -> tool result appended to memory
  -> another model round or final response
  -> Rich renderer
```

Assistant messages containing `tool_calls` are preserved, followed by one tool message per result. The latest API usage is retained for `/usage`.

## Ignore Rules

The project tree and `/init_project` scan skip version-control folders, virtual environments, caches, build output, `node_modules`, `.sandbox`, `.env*` files, binary/media files, lock files, and other generated artifacts. `search_project` searches only `.py`, `.md`, `.txt`, `.json`, `.toml`, `.yaml`, `.yml`, and `.ini` files.

## Security and Current Notes

The trust prompt is a warning, not a sandbox. After approval, `write_file` and `run_shell_command` execute with the current user's permissions. Review tool requests and do not commit API keys.

- Tavily search is provided through the configured MCP server rather than a direct Python dependency.
- `/init_project` writes `PROJECT_DESCRIPTION.md`, while prompt loading reads `CLI_AGENT.md`; the generated file is not loaded automatically.
- No test files are currently included, so setup and behavior should be verified manually.

## License

This project uses the MIT License. Anyone may use, copy, modify, distribute,
sublicense, and sell the software, provided the original copyright notice and
license text are included. See [LICENSE](LICENSE) for the complete terms.
