import json
import anyio
from typing import Any, AsyncGenerator, Dict

from cli_agents.config import AppConfig
from cli_agents.memory import ConversationMemory
from cli_agents.tools import TOOLS, execute_tool


class AIController:
    def __init__(self, client: Any, config: AppConfig, memory: ConversationMemory):
        self.client = client
        self.config = config
        self.memory = memory
        self.tools = TOOLS
        self.last_usage: Dict = {}

    # ───────────────────────────────
    # Helpers
    # ───────────────────────────────

    def reset(self) -> str:
        self.memory.reset()
        self.last_usage = {}
        return "🗑 Conversation history cleared."

    def get_last_usage(self) -> dict:
        return dict(self.last_usage)

    async def _record_usage(self, response) -> None:
        usage = getattr(response, "usage", None)
        self.last_usage = dict(usage) if usage else {}

    async def _execute_tool_safe(self, tool_name: str, arguments: dict) -> str:
        try:
            result = await anyio.to_thread.run_sync(
                lambda: execute_tool(tool_name, arguments)
            )
            return str(result)
        except Exception as e:
            return f"[Tool Error: {tool_name}] {str(e)}"

    # ───────────────────────────────
    # Main Loop (NON-STREAMING)
    # ───────────────────────────────

    async def handle_message(self, user_input: str) -> AsyncGenerator[str, None]:
        if not user_input.strip():
            return

        # Commands
        if user_input.strip() == "/reset":
            yield self.reset()
            return

        self.memory.append_user(user_input)

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
                error = f"[API Error] {exc}"
                yield error
                return

            await self._record_usage(response)

            message = response.choices[0].message
            tool_calls = getattr(message, "tool_calls", None)
            assistant_text = message.content or ""

            # ─── No tool ───
            if not tool_calls:
                self.memory.append_assistant(message)
                yield assistant_text
                return

            # ─── Tool execution ───
            self.memory.append_assistant(message)

            if assistant_text.strip():
                yield f"\n🤖 {assistant_text}\n"

            for tool_call in tool_calls:
                name = tool_call.function.name

                try:
                    args = json.loads(tool_call.function.arguments)
                except:
                    args = {}

                yield f"\n🔧 Executing: {name}\n"

                result = await self._execute_tool_safe(name, args)

                yield f"```\n{result}\n```\n"

                self.memory.append_tool(tool_call.id, name, result)

        yield "\n⚠️ Max reasoning steps reached.\n"