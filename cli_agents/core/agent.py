import asyncio
import json
from collections.abc import AsyncGenerator
from typing import Any

import anyio

from cli_agents.config import AppConfig
from cli_agents.core.mcp_manager import MCPGateway
from cli_agents.memory import ConversationMemory
from cli_agents.tools import TOOLS, execute_tool

_ERROR_PREFIX = "\x00ERROR:"
_DIFF_PREFIX = "\x00DIFF_RESULT:"


class AIController:
    def __init__(self, client: Any, config: AppConfig, memory: ConversationMemory):
        self.client = client
        self.config = config
        self.memory = memory

        self.tools = TOOLS
        self.mcp: MCPGateway | None = None
        self.last_usage: dict = {}

    # ─────────────────────────────────────────────
    # INIT & SHUTDOWN
    # ─────────────────────────────────────────────
    async def initialize(self):
        """Initialize built-in tools + MCP Gateway tools."""
        self.tools = list(TOOLS)

        if getattr(self.config, "mcp_config_path", None):
            self.mcp = MCPGateway(self.config.mcp_config_path)
            mcp_tools = await self.mcp.start()
            self.tools.extend(mcp_tools)

    async def shutdown(self):
        if self.mcp:
            await self.mcp.shutdown()

    # ─────────────────────────────────────────────
    # MEMORY & METRICS
    # ─────────────────────────────────────────────
    def reset(self) -> str:
        self.memory.reset()
        self.last_usage = {}
        return "🗑 Conversation history cleared."

    def get_last_usage(self) -> dict:
        return dict(self.last_usage)

    async def _record_usage(self, response: Any) -> None:
        usage = getattr(response, "usage", None)
        self.last_usage = dict(usage) if usage else {}

    # ─────────────────────────────────────────────
    # TOOL ROUTING & EXECUTION
    # ─────────────────────────────────────────────
    def _is_mcp_tool(self, tool_name: str) -> bool:
        return "__" in tool_name and self.mcp is not None

    async def _execute_tool_safe(self, tool_name: str, arguments: dict) -> str:
        try:
            # ── MCP TOOL ─────────────────────────────
            if self._is_mcp_tool(tool_name):
                timeout = getattr(self.config, "mcp_timeout_seconds", 60)
                return await asyncio.wait_for(
                    self.mcp.call(tool_name, arguments), timeout=timeout
                )

            # ── LOCAL TOOL ───────────────────────────
            result = await anyio.to_thread.run_sync(
                lambda: execute_tool(tool_name, arguments, self.config)
            )
            return str(result)

        except TimeoutError:
            return f"[Timeout] Tool '{tool_name}' took longer than expected"
        except Exception as e:
            return f"[Tool Error: {tool_name}] {e!s}"

    # ─────────────────────────────────────────────
    # TOKEN OPTIMIZATION: TOOL PRUNING
    # ─────────────────────────────────────────────
    def _get_optimized_tools(self) -> list:
        """
        Reduces input tokens by pruning tools based on current context.
        Always keeps essential navigation tools.
        """
        if not self.tools:
            return []

        # Essential tools always available
        essential = {"read_file", "list_folder", "search_project", "run_shell_command"}
        
        # Simple context heuristic: if the last message mentions 'diff' or 'git', keep diff tools
        last_msg = self.memory.get_messages()[-1]["content"] if self.memory.get_messages() else ""
        last_msg_lower = str(last_msg).lower()
        
        filtered = []
        for tool in self.tools:
            name = tool["function"]["name"]
            # Keep if essential, or if it matches the context keyword
            if any(e in name for e in essential):
                filtered.append(tool)
            elif "diff" in name and ("diff" in last_msg_lower or "git" in last_msg_lower):
                filtered.append(tool)
            elif "git" in name and ("git" in last_msg_lower):
                filtered.append(tool)
            # For MCP tools, we keep them as they are typically specific
            elif self._is_mcp_tool(name):
                filtered.append(tool)
            # Fallback: If the tool list is small (< 10), just keep all
            elif len(self.tools) <= 10:
                filtered.append(tool)
        
        return filtered if filtered else self.tools

    # ─────────────────────────────────────────────
    # MAIN AGENTIC LOOP
    # ─────────────────────────────────────────────
    async def handle_message(self, user_input: str) -> AsyncGenerator[str, None]:
        cleaned_input = user_input.strip()
        if not cleaned_input:
            return

        if cleaned_input == "/reset":
            yield self.reset()
            return

        self.memory.append_user(user_input)

        max_iterations = getattr(self.config, "max_iterations", 25)
        consecutive_identical_calls = 0
        last_signature = None

        for iteration in range(1, max_iterations + 1):
            # Use optimized tool list for this specific request
            current_tools = self._get_optimized_tools()

            try:
                response = await self.client.chat.completions.create(
                    model=self.config.model,
                    messages=self.memory.get_messages(),
                    tools=current_tools if current_tools else None,
                    tool_choice="auto" if current_tools else None,
                )
            except Exception as exc:
                yield f"{_ERROR_PREFIX}API request error: {exc}"
                return

            await self._record_usage(response)

            message = response.choices[0].message
            tool_calls = getattr(message, "tool_calls", None)
            assistant_text = message.content or ""

            # ── BASE CASE: Final Text Answer ──────────────────
            if not tool_calls:
                self.memory.append_assistant(message)
                yield assistant_text
                return

            # Append assistant's decision to call tools into context
            self.memory.append_assistant(message)

            if assistant_text.strip():
                yield f"\n🤖 {assistant_text}\n"

            # ── LOOP DETECTION ────────────────────────────────
            current_signature = tuple(
                (tc.function.name, tc.function.arguments) for tc in tool_calls
            )
            if current_signature == last_signature:
                consecutive_identical_calls += 1
                if consecutive_identical_calls >= 3:
                    yield f"{_ERROR_PREFIX}Tool execution aborted: Model repeated the exact same tool calls 3 times in a row."
                    return
            else:
                consecutive_identical_calls = 0
                last_signature = current_signature

            # ── PARSE ARGS & EMIT START EVENTS ────────────────
            parsed_calls: list[tuple[Any, str, dict, str]] = []
            for tc in tool_calls:
                name = tc.function.name
                args_raw = tc.function.arguments

                try:
                    args = json.loads(args_raw or "{}")
                except Exception:
                    args = {}

                args_str = json.dumps(args, ensure_ascii=False)
                parsed_calls.append((tc, name, args, args_str))

                if self._is_mcp_tool(name):
                    yield f"\x00MCP_TOOL_START:{name}:{args_str}"
                else:
                    yield f"\x00TOOL_START:{name}:{args_str}"

            # ── CONCURRENT EXECUTION ──────────────────────────
            results = await asyncio.gather(
                *(
                    self._execute_tool_safe(name, args)
                    for _, name, args, _ in parsed_calls
                )
            )

            # ── EMIT RESULTS & SYNC TO MEMORY ─────────────────
            for (tc, name, _, _), result in zip(parsed_calls, results):
                res_str = str(result)
                if res_str.startswith(("Error", "[Tool Error:", "[Timeout]")):
                    yield f"{_ERROR_PREFIX}Tool '{name}': {res_str}"

                if name == "git_diff":
                    yield f"{_DIFF_PREFIX}{res_str}"

                yield f"\x00TOOL_DONE:{name}"

                self.memory.append_tool(tc.id, name, res_str)

        yield f"\n⚠️ Max reasoning steps reached ({max_iterations} turns).\n"