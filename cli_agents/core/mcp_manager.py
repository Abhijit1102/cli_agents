import json
import os
import sys
from typing import Dict, Any, List, Tuple, Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamablehttp_client


class MCPGateway:
    """
    Universal Version-Safe MCP Gateway

    Features:
    - stdio / sse / http support
    - version-safe connection normalization
    - tool registry mapping
    - safe execution routing
    """

    def __init__(self, config_path):
        self.config_path = config_path
        self.exit_stack = AsyncExitStack()

        self.sessions: Dict[str, ClientSession] = {}
        self.tools_index: Dict[str, str] = {}  # tool_fqn -> server

    # ─────────────────────────────────────────────
    # BOOT
    # ─────────────────────────────────────────────
    async def start(self) -> List[Dict]:
        if not self.config_path.exists():
            return []

        config = json.loads(self.config_path.read_text())
        servers = config.get("mcpServers", {})

        all_tools = []

        await self.exit_stack.__aenter__()

        for name, cfg in servers.items():
            tools = await self._connect(name, cfg)
            all_tools.extend(tools)

        return all_tools

    # ─────────────────────────────────────────────
    # CONNECT (CORE FIX AREA)
    # ─────────────────────────────────────────────
    async def _connect(self, name: str, cfg: Dict) -> List[Dict]:
        try:
            transport = self._detect(cfg)

            conn = None

            # ── STDIO ─────────────────────────────
            if transport == "stdio":
                conn = await self.exit_stack.enter_async_context(
                    stdio_client(
                        StdioServerParameters(
                            command=cfg["command"],
                            args=cfg.get("args", []),
                            env={**os.environ, **cfg.get("env", {})},
                        )
                    )
                )

            # ── SSE ───────────────────────────────
            elif transport == "sse":
                conn = await self.exit_stack.enter_async_context(
                    sse_client(
                        cfg["url"],
                        headers=cfg.get("headers", {})
                    )
                )

            # ── HTTP (TAVILY FIX) ─────────────────
            elif transport == "http":
                conn = await self.exit_stack.enter_async_context(
                    streamablehttp_client(
                        cfg["url"],
                        headers=cfg.get("headers", {})
                    )
                )

            else:
                raise ValueError(f"Unknown transport: {transport}")

            # ── VERSION SAFE NORMALIZATION ─────────
            read, write = self._normalize_conn(conn)

            session = await self.exit_stack.enter_async_context(
                ClientSession(read, write)
            )

            await session.initialize()

            self.sessions[name] = session

            # ── TOOL REGISTRY ──────────────────────
            tools = []
            res = await session.list_tools()

            for t in res.tools:
                fqn = f"{name}__{t.name}"
                self.tools_index[fqn] = name
                tools.append(self._to_openai(name, t))

            print(
                f"[MCP] ✅ {name} ({transport}) tools={len(tools)}",
                file=sys.stderr
            )

            return tools

        except Exception as e:
            print(f"[MCP] ❌ {name} failed: {e}", file=sys.stderr)
            return []

    # ─────────────────────────────────────────────
    # VERSION SAFE NORMALIZER (KEY FIX)
    # ─────────────────────────────────────────────
    def _normalize_conn(self, conn):
        """
        Forces ALL MCP versions → (read, write)
        """

        # tuple responses (most MCP versions)
        if isinstance(conn, tuple):
            if len(conn) == 2:
                return conn
            if len(conn) >= 3:
                return conn[0], conn[1]

        # object-style responses (future MCP)
        if hasattr(conn, "read") and hasattr(conn, "write"):
            return conn.read, conn.write

        raise ValueError(f"Unknown MCP connection format: {type(conn)}")

    # ─────────────────────────────────────────────
    # TOOL CALL ROUTER
    # ─────────────────────────────────────────────
    async def call(self, tool_fqn: str, args: Dict) -> str:
        server, _, tool = tool_fqn.partition("__")

        session = self.sessions.get(server)
        if not session:
            return f"[MCP Error] server '{server}' not connected"

        try:
            res = await session.call_tool(tool, args)
            return self._extract(res.content)
        except Exception as e:
            return f"[MCP Error] {e}"

    # ─────────────────────────────────────────────
    # TRANSPORT DETECTION
    # ─────────────────────────────────────────────
    def _detect(self, cfg: Dict) -> str:
        if "command" in cfg:
            return "stdio"
        if cfg.get("transport") == "http":
            return "http"
        return "sse"

    # ─────────────────────────────────────────────
    # SAFE CONTENT EXTRACTION
    # ─────────────────────────────────────────────
    def _extract(self, content):
        if not content:
            return ""

        out = []

        for c in content:
            if isinstance(c, dict):
                out.append(c.get("text") or str(c))
            elif hasattr(c, "text"):
                out.append(c.text)
            elif hasattr(c, "data"):
                out.append(str(c.data))
            else:
                out.append(str(c))

        return "\n".join(out)

    # ─────────────────────────────────────────────
    # TOOL FORMATTER
    # ─────────────────────────────────────────────
    def _to_openai(self, server, tool):
        return {
            "type": "function",
            "function": {
                "name": f"{server}__{tool.name}",
                "description": tool.description or "",
                "parameters": tool.inputSchema or {"type": "object"},
            }
        }

    # ─────────────────────────────────────────────
    # SHUTDOWN
    # ─────────────────────────────────────────────
    async def shutdown(self):
        await self.exit_stack.aclose()