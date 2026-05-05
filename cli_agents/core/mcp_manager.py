import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class MCPManager:
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.exit_stack = AsyncExitStack()
        self.sessions: Dict[str, ClientSession] = {}

    async def start_servers(self) -> List[Dict]:
        if not self.config_path.exists():
            return []

        with open(self.config_path, "r") as f:
            config = json.load(f)

        all_tools = []
        servers = config.get("mcpServers", {})

        for name, srv_cfg in servers.items():
            try:
                # Merge env carefully — on Windows PATH must be inherited
                env = {**os.environ, **srv_cfg.get("env", {})}

                params = StdioServerParameters(
                    command=srv_cfg["command"],
                    args=srv_cfg.get("args", []),
                    env=env,
                )

                read, write = await self.exit_stack.enter_async_context(
                    stdio_client(params)
                )
                session = await self.exit_stack.enter_async_context(
                    ClientSession(read, write)
                )

                await session.initialize()
                self.sessions[name] = session

                response = await session.list_tools()
                for tool in response.tools:
                    all_tools.append(self._to_openai_tool(name, tool))

                print(f"[MCP] ✅ {name} connected ({len(response.tools)} tools)", 
                      file=sys.stderr)

            except Exception as e:
                # Don't crash the whole app — log and skip this server
                print(f"[MCP] ❌ Failed to start '{name}': {e}", file=sys.stderr)

        return all_tools

    def _to_openai_tool(self, server_name: str, tool: Any) -> Dict:
        return {
            "type": "function",
            "function": {
                "name": f"{server_name}__{tool.name}",
                "description": tool.description,
                "parameters": tool.inputSchema,
            },
        }

    async def call_tool(self, tool_call_name: str, arguments: Dict) -> str:
        server_name, _, tool_name = tool_call_name.partition("__")
        if server_name not in self.sessions:
            return f"Error: MCP Server '{server_name}' not found or failed to start."
        try:
            result = await self.sessions[server_name].call_tool(tool_name, arguments)
            return str(result.content)
        except Exception as e:
            return f"[MCP Tool Error: {tool_call_name}] {e}"

    async def shutdown(self):
        await self.exit_stack.aclose()