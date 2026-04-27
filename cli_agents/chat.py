import json
import anyio
from typing import List, Dict

from cli_agents.tools import TOOLS, execute_tool


class ChatAgent:
    def __init__(self, client, system_prompt: str, model: str):
        self.client = client
        self.model = model
        self.history: List[Dict] = [
            {"role": "system", "content": system_prompt}
        ]
        self.last_usage: dict = {}

    def reset(self):
        self.history = [self.history[0]]
        self.last_usage = {}

    def get_last_usage(self) -> dict:
        return self.last_usage or {}

    async def handle_message(self, user_input: str):
        if user_input.strip() == "/reset":
            self.reset()
            yield "🗑 History cleared."
            return

        self.history.append({"role": "user", "content": user_input})

        while True:
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=self.history,
                    tools=TOOLS,
                    tool_choice="auto",
                    stream=False,
                )
            except Exception as e:
                yield f"[API Error] {e}"
                self.history.pop()
                return

            usage = getattr(response, "usage", None)
            if usage:
                if isinstance(usage, dict):
                    self.last_usage = usage
                else:
                    try:
                        self.last_usage = dict(usage)
                    except Exception:
                        self.last_usage = {k: getattr(usage, k) for k in dir(usage) if not k.startswith("_")}
            else:
                self.last_usage = {}

            msg = response.choices[0].message

            # ✅ No tool calls → return response
            if not msg.tool_calls:
                reply = msg.content or ""
                self.history.append({"role": "assistant", "content": reply})

                for word in reply.split(" "):
                    yield word + " "
                    await anyio.sleep(0.01)
                break

            # ✅ Handle tool calls
            self.history.append(msg)

            tool_results = []
            for tc in msg.tool_calls:
                name = tc.function.name
                args = json.loads(tc.function.arguments)

                yield f"\n🔧 `{name}` {args}\n"

                result = await anyio.to_thread.run_sync(
                    lambda: execute_tool(name, args)
                )

                yield f"```\n{result}\n```\n"

                tool_results.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })

            self.history.extend(tool_results)
