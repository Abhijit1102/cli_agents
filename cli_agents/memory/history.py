from typing import List, Dict


class ConversationMemory:
    def __init__(self, system_prompt: str):
        self.messages: List[Dict[str, str]] = [
            {"role": "system", "content": system_prompt}
        ]
        self.tool_log: List[Dict[str, str]] = []

    def reset(self) -> None:
        self.messages = [self.messages[0]] if self.messages else []
        self.tool_log = []

    def append_user(self, content: str) -> None:
        self.messages.append({"role": "user", "content": content})

    def append_assistant(self, content: str) -> None:
        self.messages.append({"role": "assistant", "content": content})

    def append_tool(self, name: str, content: str) -> None:
        self.tool_log.append({"tool": name, "result": content})
        self.messages.append({"role": "tool", "content": content})

    def get_messages(self) -> List[Dict[str, str]]:
        return list(self.messages)
