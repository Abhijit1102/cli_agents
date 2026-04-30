import json
import anyio
from typing import Any, AsyncGenerator

from cli_agents.config import AppConfig
from cli_agents.memory import ConversationMemory
from cli_agents.tools import TOOLS, execute_tool


class AIController:
    def __init__(self, client: Any, config: AppConfig, memory: ConversationMemory):
        self.client = client
        self.config = config
        self.memory = memory
        self.tools = TOOLS
        self.last_usage: dict = {}

    def reset(self) -> str:
        self.memory.reset()
        self.last_usage = {}
        return "🗑 Conversation history cleared."

    def get_last_usage(self) -> dict:
        return dict(self.last_usage)

    def _stream_text(self, text: str) -> AsyncGenerator[str, None]:
        words = text.split(" ")
        for token in words:
            yield token + " "

    async def _record_usage(self, response) -> None:
        usage = getattr(response, "usage", None)
        if usage is None:
            self.last_usage = {}
            return

        if isinstance(usage, dict):
            self.last_usage = usage
            return

        try:
            self.last_usage = dict(usage)
        except Exception:
            self.last_usage = {k: getattr(usage, k) for k in dir(usage) if not k.startswith("_")}

    async def handle_message(self, user_input: str) -> AsyncGenerator[str, None]:
        normalized = user_input.strip()
        if not normalized:
            return

        if normalized == "/reset":
            yield self.reset()
            return

        if normalized.startswith("/run "):
            command = normalized[5:].strip()
            result = await anyio.to_thread.run_sync(
                lambda: execute_tool("run_shell_command", {"command": command, "timeout": 30})
            )
            self.memory.append_user(user_input)
            self.memory.append_tool("run_shell_command", result)
            yield result
            return

        self.memory.append_user(user_input)
        iteration = 0

        while iteration < 4:
            iteration += 1
            try:
                response = await self.client.chat.completions.create(
                    model=self.config.model,
                    messages=self.memory.get_messages(),
                    tools=self.tools,
                    tool_choice="auto",
                    stream=False,
                )
            except Exception as exc:
                error = f"[API Error] {exc}"
                self.memory.append_assistant(error)
                yield error
                return

            await self._record_usage(response)
            message = response.choices[0].message
            tool_calls = getattr(message, "tool_calls", None)
            assistant_text = message.content or ""

            if not tool_calls:
                self.memory.append_assistant(assistant_text)
                for token in self._stream_text(assistant_text):
                    yield token
                return

            self.memory.append_assistant(assistant_text)
            for tool_call in tool_calls:
                tool_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)
                yield f"\n🔧 Executing tool: {tool_name} {arguments}\n"

                tool_result = await anyio.to_thread.run_sync(
                    lambda: execute_tool(tool_name, arguments)
                )
                yield f"```
{tool_result}
```\n"
                self.memory.append_tool(tool_name, tool_result)

        yield "[agent] reached maximum tool reasoning steps. Please verify the prompt or break the task into smaller requests."
