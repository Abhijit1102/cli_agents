from typing import List, Dict, Any


class ConversationMemory:
    def __init__(self, system_prompt: str):
        self.messages: List[Dict[str, Any]] = [
            {"role": "system", "content": system_prompt}
        ]
        self.tool_log: List[Dict[str, str]] = []

    def reset(self) -> None:
        self.messages = [self.messages[0]] if self.messages else []
        self.tool_log = []

    def append_user(self, content: str) -> None:
        self.messages.append({"role": "user", "content": content})

    def append_assistant(self, message: Any) -> None:
        """Store the full assistant message object to preserve tool_calls."""
        if hasattr(message, "model_dump"):
            dumped = message.model_dump()
            dumped = {k: v for k, v in dumped.items() if v is not None}
            self.messages.append(dumped)
        elif isinstance(message, dict):
            self.messages.append(message)
        else:
            self.messages.append({"role": "assistant", "content": str(message)})

    def append_tool(self, tool_call_id: str, name: str, content: str) -> None:
        """Append a tool result — must match a tool_call_id from the last assistant message."""
        self.tool_log.append({"tool": name, "result": content})
        self.messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": name,
            "content": content,
        })

    def get_messages(self) -> List[Dict[str, Any]]:
        return list(self.messages)