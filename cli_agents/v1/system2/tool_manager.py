import asyncio
import anyio
from cli_agents.config import AppConfig
from cli_agents.core.mcp_manager import MCPGateway
from cli_agents.tools import execute_tool

class ToolManager:
    """Handles the actual execution of tools, abstracting away MCP vs Local."""
    def __init__(self, config: AppConfig, mcp: MCPGateway | None = None, system1_engine=None):
        self.config = config
        self.mcp = mcp
        self.system1 = system1_engine

    def is_mcp_tool(self, tool_name: str) -> bool:
        return "__" in tool_name and self.mcp is not None

    async def execute(self, tool_name: str, arguments: dict) -> str:
        try:
            # --- Special Handling for System 1 Delegation ---
            # This allows System 2 to call System 1 for quick classification/decisions
            if tool_name == "system1_classify" and self.system1:
                content = arguments.get("content", "")
                prompt = arguments.get("prompt", "Classify this content.")
                return await self.system1.classify_content(content, prompt)

            if self.is_mcp_tool(tool_name):
                timeout = getattr(self.config, "mcp_timeout_seconds", 60)
                return await asyncio.wait_for(
                    self.mcp.call(tool_name, arguments), timeout=timeout
                )

            result = await anyio.to_thread.run_sync(
                lambda: execute_tool(tool_name, arguments, self.config)
            )
            return str(result)
        except Exception as e:
            error_msg = str(e)
            if "validation error" in error_msg.lower() or "field required" in error_msg.lower():
                return f"[Validation Error] The tool '{tool_name}' is missing required arguments. {error_msg}. Please check the tool definition and try again with all required fields."
            return f"[Tool Error: {tool_name}] {error_msg}"
