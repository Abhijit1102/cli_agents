from typing import List, Dict, Any


class ConversationMemory:
    def __init__(self, system_prompt: str):
        self.messages: List[Dict[str, Any]] = [
            {"role": "system", "content": system_prompt}
        ]
        self.tool_log: List[Dict[str, str]] = []
        self.max_history = 20  # Token guard: keep history lean

    def reset(self) -> None:
        self.messages = [self.messages[0]] if self.messages else []
        self.tool_log = []

    def append_user(self, content: str) -> None:
        self.messages.append({"role": "user", "content": content})
        self._enforce_limit()

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
        self._enforce_limit()

    def append_tool(self, tool_call_id: str, name: str, content: str) -> None:
        """Append a tool result — must match a tool_call_id from the last assistant message."""
        self.tool_log.append({"tool": name, "result": content})
        self.messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": name,
            "content": content,
        })
        self._enforce_limit()

    def _enforce_limit(self) -> None:
        """Prevents context window bloat by keeping only the last N messages."""
        if len(self.messages) > self.max_history:
            system_msg = self.messages[0]
            # Keep system prompt + most recent messages
            self.messages = [system_msg] + self.messages[-(self.max_history - 1):]

    def compact(self, summary: str) -> None:
        """
        Compresses the history by replacing everything between the system prompt 
        and the most recent messages with a single summary message.
        """
        if len(self.messages) <= 2:
            return

        system_msg = self.messages[0]
        recent_context = self.messages[-4:] if len(self.messages) > 5 else []
        
        self.messages = [
            system_msg,
            {"role": "system", "content": f"Conversation Summary: {summary}"},
            *recent_context
        ]

    def get_messages(self) -> List[Dict[str, Any]]:
        return list(self.messages)