import json
import anyio
import asyncio
from typing import Any, AsyncGenerator, Dict

from cli_agents.config import AppConfig
from cli_agents.memory import ConversationMemory
from cli_agents.tools import TOOLS, execute_tool

# 👉 Use Gateway (recommended)
from cli_agents.core.mcp_manager import MCPGateway

_ERROR_PREFIX = "\x00ERROR:"


class AIController:
    def __init__(self, client: Any, config: AppConfig, memory: ConversationMemory):
        self.client = client
        self.config = config
        self.memory = memory

        self.tools = TOOLS
        self.mcp = None

        self.last_usage: Dict = {}

    # ─────────────────────────────────────────────
    # INIT
    # ─────────────────────────────────────────────
    async def initialize(self):
        """Initialize tools + MCP Gateway"""
        self.tools = list(TOOLS)

        if self.config.mcp_config_path:
            self.mcp = MCPGateway(self.config.mcp_config_path)
            mcp_tools = await self.mcp.start()
            self.tools.extend(mcp_tools)

    # ─────────────────────────────────────────────
    # SHUTDOWN
    # ─────────────────────────────────────────────
    async def shutdown(self):
        if self.mcp:
            await self.mcp.shutdown()

    # ─────────────────────────────────────────────
    # MEMORY OPS
    # ─────────────────────────────────────────────
    def reset(self) -> str:
        self.memory.reset()
        self.last_usage = {}
        return "🗑 Conversation history cleared."

    def get_last_usage(self) -> dict:
        return dict(self.last_usage)

    async def _record_usage(self, response) -> None:
        usage = getattr(response, "usage", None)
        self.last_usage = dict(usage) if usage else {}

    # ─────────────────────────────────────────────
    # TOOL ROUTING CHECK
    # ─────────────────────────────────────────────
    def _is_mcp_tool(self, tool_name: str) -> bool:
        return "__" in tool_name and self.mcp is not None

    # ─────────────────────────────────────────────
    # TOOL EXECUTION (SAFE)
    # ─────────────────────────────────────────────
    async def _execute_tool_safe(self, tool_name: str, arguments: dict) -> str:
        try:
            # ── MCP TOOL ─────────────────────────────
            if self._is_mcp_tool(tool_name):
                print(f"[MCP CALL] {tool_name} {arguments}")

                return await asyncio.wait_for(
                    self.mcp.call(tool_name, arguments),
                    timeout=60
                )

            # ── LOCAL TOOL ───────────────────────────
            result = await anyio.to_thread.run_sync(
                lambda: execute_tool(tool_name, arguments, self.config)
            )

            return str(result)

        except asyncio.TimeoutError:
            return f"[Timeout] Tool '{tool_name}' took too long"

        except Exception as e:
            return f"[Tool Error: {tool_name}] {str(e)}"

    # ─────────────────────────────────────────────
    # MAIN LOOP
    # ─────────────────────────────────────────────
    async def handle_message(self, user_input: str) -> AsyncGenerator[str, None]:

        if not user_input.strip():
            return

        if user_input.strip() == "/reset":
            yield self.reset()
            return

        self.memory.append_user(user_input)

        _DIFF_PREFIX = "\x00DIFF_RESULT:"
        max_iterations = 4

        for _ in range(max_iterations):
            try:
                response = await self.client.chat.completions.create(
                    model=self.config.model,
                    messages=self.memory.get_messages(),
                    tools=self.tools,
                    tool_choice="auto",
                )
            except Exception as exc:
                yield f"{_ERROR_PREFIX}API request: {exc}"
                return

            await self._record_usage(response)

            message = response.choices[0].message
            tool_calls = getattr(message, "tool_calls", None)
            assistant_text = message.content or ""

            # ── NO TOOL CALL ─────────────────────────
            if not tool_calls:
                self.memory.append_assistant(message)
                yield assistant_text
                return

            # ── TOOL CALLS ───────────────────────────
            self.memory.append_assistant(message)

            if assistant_text.strip():
                yield f"\n🤖 {assistant_text}\n"

            for tool_call in tool_calls:
                name = tool_call.function.name
                args_raw = tool_call.function.arguments

                try:
                    args = json.loads(args_raw or "{}")
                except Exception:
                    args = {}

                args_str = json.dumps(args, ensure_ascii=False)

                # UI SIGNALS
                if self._is_mcp_tool(name):
                    yield f"\x00MCP_TOOL_START:{name}:{args_str}"
                else:
                    yield f"\x00TOOL_START:{name}:{args_str}"

                # EXECUTE TOOL
                result = await self._execute_tool_safe(name, args)

                if result.startswith(("Error", "[Tool Error:", "[Timeout]")):
                    yield f"{_ERROR_PREFIX}Tool '{name}': {result}"

                # SPECIAL: git diff
                if name == "git_diff":
                    yield f"{_DIFF_PREFIX}{result}"

                yield f"\x00TOOL_DONE:{name}"

                self.memory.append_tool(tool_call.id, name, result)

        yield "\n⚠️ Max reasoning steps reached.\n"