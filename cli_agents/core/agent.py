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
    # Public Helpers
    # ───────────────────────────────

    def reset(self) -> str:
        self.memory.reset()
        self.last_usage = {}
        return "🗑 Conversation history cleared."

    def get_last_usage(self) -> dict:
        return dict(self.last_usage)

    # ───────────────────────────────
    # Streaming Utility (better UX)
    # ───────────────────────────────

    async def _stream_text(self, text: str) -> AsyncGenerator[str, None]:
        for i in range(0, len(text), 4):  # chunked streaming
            yield text[i:i + 4]
            await anyio.sleep(0.01)

    # ───────────────────────────────
    # Usage Tracking
    # ───────────────────────────────

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
            self.last_usage = {
                k: getattr(usage, k)
                for k in dir(usage)
                if not k.startswith("_")
            }

    # ───────────────────────────────
    # Safe Tool Execution
    # ───────────────────────────────

    async def _execute_tool_safe(self, tool_name: str, arguments: dict) -> str:
        try:
            result = await anyio.to_thread.run_sync(
                lambda: execute_tool(tool_name, arguments)
            )
            return str(result)
        except Exception as e:
            return f"[Tool Error] {str(e)}"

    # ───────────────────────────────
    # Core Agent Loop
    # ───────────────────────────────

    async def handle_message(self, user_input: str) -> AsyncGenerator[str, None]:
        normalized = user_input.strip()

        if not normalized:
            return

        # ─── Commands ─────────────────
        if normalized == "/reset":
            yield self.reset()
            return

        if normalized.startswith("/run "):
            command = normalized[5:].strip()

            result = await self._execute_tool_safe(
                "run_shell_command",
                {"command": command, "timeout": 30},
            )

            self.memory.append_user(user_input)
            self.memory.append_tool("run_shell_command", result)

            yield f"\n🖥 Running command:\n```bash\n{command}\n```\n"
            yield f"```\n{result}\n```\n"
            return

        # ─── Normal Chat Flow ─────────
        self.memory.append_user(user_input)

        max_iterations = 4
        iteration = 0

        while iteration < max_iterations:
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

            # ─── Case 1: No tool needed ───
            if not tool_calls:
                self.memory.append_assistant(assistant_text)

                async for chunk in self._stream_text(assistant_text):
                    yield chunk
                return

            # ─── Case 2: Tool calls ───────
            self.memory.append_assistant(assistant_text)

            if assistant_text.strip():
                yield f"\n🤖 {assistant_text}\n"

            for tool_call in tool_calls:
                tool_name = tool_call.function.name

                try:
                    arguments = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    arguments = {}

                yield f"\n🔧 Executing: {tool_name}\n"
                yield f"📥 Args: {json.dumps(arguments, indent=2)}\n"

                tool_result = await self._execute_tool_safe(tool_name, arguments)

                yield f"\n📤 Result:\n```\n{tool_result}\n```\n"

                self.memory.append_tool(tool_name, tool_result)

        # ─── Max Iteration Safety ─────
        yield "\n⚠️ Agent reached max reasoning steps.\nTry breaking the task into smaller parts.\n"