import asyncio
import json
from collections.abc import AsyncGenerator
from typing import Any
import anyio
from openai import AsyncOpenAI

from cli_agents.config import AppConfig
from cli_agents.memory import ConversationMemory
from cli_agents.v1.core.base import BaseProcess
from cli_agents.v1.system2.tool_manager import ToolManager

class System2Planner(BaseProcess):
    def __init__(
        self, 
        system2_client: AsyncOpenAI, 
        config: AppConfig, 
        memory: ConversationMemory,
        tool_manager: ToolManager
    ):
        self.client = system2_client
        self.config = config
        self.memory = memory
        self.tool_manager = tool_manager

    def _truncate_result(self, result: str, max_chars: int = 8000) -> str:
        """Prevent massive tool outputs from bloating tokens."""
        if len(result) <= max_chars:
            return result
        return result[:max_chars] + f"\n\n... [Truncated: result too long ({len(result)} chars)] ..."

    async def execute(self, tools: list, yield_func: Any) -> None:
        """Implements the ReAct reasoning loop."""
        max_iterations = getattr(self.config, "max_iterations", 25)
        last_signature = None
        consecutive_identical_calls = 0

        for iteration in range(1, max_iterations + 1):
            try:
                response = await self.client.chat.completions.create(
                    model=self.config.model,
                    messages=self.memory.get_messages(),
                    tools=tools if tools else None,
                    tool_choice="auto" if tools else None,
                )
            except Exception as exc:
                await yield_func(f"\x00ERROR:API request error: {exc}")
                return

            message = response.choices[0].message
            tool_calls = getattr(message, "tool_calls", None)
            assistant_text = message.content or ""

            if not tool_calls:
                self.memory.append_assistant(message)
                await yield_func(assistant_text)
                return

            self.memory.append_assistant(message)
            if assistant_text.strip():
                await yield_func(f"\n🤖 {assistant_text}\n")

            # Loop Detection
            current_signature = tuple(
                (tc.function.name, tc.function.arguments) for tc in tool_calls
            )
            if current_signature == last_signature:
                consecutive_identical_calls += 1
                if consecutive_identical_calls >= 2: # Warn at 2, Abort at 4
                    # Inject a strong warning into memory to force the model to pivot
                    warning_msg = (
                        "⚠️ SYSTEM WARNING: You are repeating the exact same tool call. "
                        "The previous result was not helpful. Please try a different tool, "
                        "different arguments, or a different strategy to solve the problem."
                    )
                    # We use a tool-like result to force it into the prompt
                    self.memory.append_tool(
                        tool_call_id="system_warning", 
                        tool_name="system_hint", 
                        result=warning_msg
                    )
                    await yield_func(f"\x00SYSTEM_HINT:{warning_msg}")
                    
                if consecutive_identical_calls >= 4:
                    await yield_func("\x00ERROR:Tool execution aborted: Model repeated same calls too many times.")
                    return
            else:
                consecutive_identical_calls = 0
                last_signature = current_signature

            # Tool Execution
            parsed_calls = []
            for tc in tool_calls:
                name = tc.function.name
                args = json.loads(tc.function.arguments or "{}")
                args_str = json.dumps(args, ensure_ascii=False)
                parsed_calls.append((tc, name, args, args_str))
                await yield_func(f"\x00{'MCP_' if self.tool_manager.is_mcp_tool(name) else ''}TOOL_START:{name}:{args_str}")

            results = await asyncio.gather(
                *(self.tool_manager.execute(n, a) for _, n, a, _ in parsed_calls)
            )

            for (tc, name, _, _), result in zip(parsed_calls, results):
                res_str = str(result)
                
                # TOKEN OPTIMIZATION: Truncate massive tool outputs
                res_str = self._truncate_result(res_str)

                if res_str.startswith(("Error", "[Tool Error:", "[Timeout]")):
                    await yield_func(f"\x00ERROR:Tool '{name}': {res_str}")
                if name == "git_diff":
                    await yield_func(f"\x00DIFF_RESULT:{res_str}")
                await yield_func(f"\x00TOOL_DONE:{name}")
                self.memory.append_tool(tc.id, name, res_str)

        await yield_func(f"\n⚠️ Max reasoning steps reached ({max_iterations} turns).\n")
