import json
import os
import sys
import asyncio
from typing import Dict, Any, List, Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamable_http_client


# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
CONNECT_TIMEOUT   = 15   # seconds to wait for session.initialize()
TOOL_CALL_TIMEOUT = 60   # seconds to wait for a tool response
MAX_RETRIES       = 3    # number of connection attempts per server
RETRY_DELAY       = 1.5  # seconds between retries


class MCPGateway:
    """
    Universal Version-Safe MCP Gateway

    Features:
    - stdio / sse / streamable-http support
    - explicit transport detection (no silent fallthrough on typos)
    - connection timeout guard (prevents CancelledError hangs)
    - automatic retry with backoff
    - api_key shorthand in config → Authorization header
    - version-safe connection normalization
    - tool registry mapping
    - safe content extraction
    """

    def __init__(self, config_path):
        self.config_path = config_path
        self.exit_stack  = AsyncExitStack()

        self.sessions:     Dict[str, ClientSession] = {}
        self.tools_index:  Dict[str, str]           = {}  # fqn → server name

    # ─────────────────────────────────────────────
    # BOOT
    # ─────────────────────────────────────────────
    async def start(self) -> List[Dict]:
        if not self.config_path.exists():
            print("[MCP] No config file found — skipping MCP init.", file=sys.stderr)
            return []

        config  = json.loads(self.config_path.read_text())
        servers = config.get("mcpServers", {})

        all_tools: List[Dict] = []

        await self.exit_stack.__aenter__()

        for name, cfg in servers.items():
            tools = await self._connect_with_retry(name, cfg)
            all_tools.extend(tools)

        return all_tools

    # ─────────────────────────────────────────────
    # RETRY WRAPPER
    # ─────────────────────────────────────────────
    async def _connect_with_retry(self, name: str, cfg: Dict) -> List[Dict]:
        last_error: Optional[Exception] = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                return await self._connect(name, cfg)

            except Exception as e:
                last_error = e
                if attempt < MAX_RETRIES:
                    print(
                        f"[MCP] ⚠ {name} attempt {attempt}/{MAX_RETRIES} failed: {e} "
                        f"— retrying in {RETRY_DELAY}s…",
                        file=sys.stderr,
                    )
                    await asyncio.sleep(RETRY_DELAY)

        print(
            f"[MCP] ❌ {name} failed after {MAX_RETRIES} attempts: {last_error}",
            file=sys.stderr,
        )
        return []

    # ─────────────────────────────────────────────
    # CONNECT (single attempt)
    # ─────────────────────────────────────────────
    async def _connect(self, name: str, cfg: Dict) -> List[Dict]:
        transport = self._detect(name, cfg)
        headers   = self._build_headers(cfg)

        conn = None

        # ── STDIO ─────────────────────────────────
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

        # ── SSE ───────────────────────────────────
        elif transport == "sse":
            conn = await self.exit_stack.enter_async_context(
                sse_client(cfg["url"], headers=headers)
            )

        # ── STREAMABLE HTTP ────────────────────────
        elif transport == "http":
            conn = await self.exit_stack.enter_async_context(
                streamable_http_client(cfg["url"], headers=headers)
            )

        else:
            raise ValueError(f"Unknown transport '{transport}' for server '{name}'")

        # ── VERSION-SAFE NORMALIZATION ─────────────
        read, write = self._normalize_conn(conn)

        session = await self.exit_stack.enter_async_context(
            ClientSession(read, write)
        )

        # ── TIMEOUT GUARD ─────────────────────────
        try:
            await asyncio.wait_for(session.initialize(), timeout=CONNECT_TIMEOUT)
        except asyncio.TimeoutError:
            raise TimeoutError(
                f"session.initialize() timed out after {CONNECT_TIMEOUT}s "
                f"— is the server running at {cfg.get('url', cfg.get('command'))}?"
            )

        self.sessions[name] = session

        # ── TOOL REGISTRY ──────────────────────────
        tools: List[Dict] = []
        res = await session.list_tools()

        for t in res.tools:
            fqn = f"{name}__{t.name}"
            self.tools_index[fqn] = name
            tools.append(self._to_openai(name, t))

        print(
            f"[MCP] ✅ {name} ({transport}) tools={len(tools)}",
            file=sys.stderr,
        )
        return tools

    # ─────────────────────────────────────────────
    # TRANSPORT DETECTION  (explicit, no silent fallthrough)
    # ─────────────────────────────────────────────
    def _detect(self, name: str, cfg: Dict) -> str:
        # stdio: always signalled by "command" key
        if "command" in cfg:
            return "stdio"

        transport = cfg.get("transport", "sse").lower().strip()

        if transport in ("http", "streamable-http", "streamable_http"):
            return "http"

        if transport in ("sse", ""):
            return "sse"

        # Unknown value — warn and fall back to SSE rather than silently breaking
        print(
            f"[MCP] ⚠ {name}: unknown transport '{transport}', "
            f"falling back to 'sse'. Valid values: sse | http | streamable-http",
            file=sys.stderr,
        )
        return "sse"

    # ─────────────────────────────────────────────
    # HEADER BUILDER  (supports api_key shorthand)
    # ─────────────────────────────────────────────
    def _build_headers(self, cfg: Dict) -> Dict[str, str]:
        headers = dict(cfg.get("headers", {}))

        # Shorthand: "api_key": "sk-..." → Authorization: Bearer sk-...
        api_key = cfg.get("api_key")
        if api_key and "Authorization" not in headers:
            headers["Authorization"] = f"Bearer {api_key}"

        return headers

    # ─────────────────────────────────────────────
    # VERSION-SAFE NORMALIZER
    # ─────────────────────────────────────────────
    def _normalize_conn(self, conn):
        """Forces ALL MCP transport versions → (read, write)"""

        if isinstance(conn, tuple):
            if len(conn) == 2:
                return conn
            if len(conn) >= 3:
                return conn[0], conn[1]

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
            res = await asyncio.wait_for(
                session.call_tool(tool, args),
                timeout=TOOL_CALL_TIMEOUT,
            )
            return self._extract(res.content)

        except asyncio.TimeoutError:
            return (
                f"[MCP Timeout] '{tool_fqn}' did not respond "
                f"within {TOOL_CALL_TIMEOUT}s"
            )

        except Exception as e:
            return f"[MCP Error] {tool_fqn}: {e}"

    # ─────────────────────────────────────────────
    # SAFE CONTENT EXTRACTION
    # ─────────────────────────────────────────────
    def _extract(self, content) -> str:
        if not content:
            return ""

        out: List[str] = []

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
    # TOOL FORMATTER  (OpenAI-compatible schema)
    # ─────────────────────────────────────────────
    def _to_openai(self, server: str, tool) -> Dict:
        return {
            "type": "function",
            "function": {
                "name":        f"{server}__{tool.name}",
                "description": tool.description or "",
                "parameters":  tool.inputSchema or {"type": "object"},
            },
        }

    # ─────────────────────────────────────────────
    # SHUTDOWN
    # ─────────────────────────────────────────────
    async def shutdown(self):
        await self.exit_stack.aclose()
        print("[MCP] All servers disconnected.", file=sys.stderr)