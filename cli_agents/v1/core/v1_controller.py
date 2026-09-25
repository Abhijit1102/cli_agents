import asyncio
import json
from collections.abc import AsyncGenerator
from typing import Any

from openai import AsyncOpenAI
from cli_agents.config import AppConfig
from cli_agents.core.mcp_manager import MCPGateway
from cli_agents.memory import ConversationMemory
from cli_agents.tools import TOOLS

from cli_agents.v1.system1.heuristics import DynamicIntentEngine
from cli_agents.v1.system2.planner import System2Planner, ToolManager

class V1AIController:
    """
    Unified AI Controller for V1.
    Orchestrates System 1 (Reflexive) and System 2 (Deliberative).
    """

    def __init__(
        self, client: AsyncOpenAI, config: AppConfig, memory: ConversationMemory
    ):
        self.config = config
        self.memory = memory
        self.client = client
        
        # Initialize System 1
        self.system1 = DynamicIntentEngine(config)
        
        # Component State
        self.tools = list(TOOLS)
        self.mcp: MCPGateway | None = None
        self.tool_manager: ToolManager | None = None
        self.planner: System2Planner | None = None
        self.last_usage: dict = {}

    async def initialize(self):
        """Setup infrastructure and System 2 components."""
        if getattr(self.config, "mcp_config_path", None):
            self.mcp = MCPGateway(self.config.mcp_config_path)
            mcp_tools = await self.mcp.start()
            self.tools.extend(mcp_tools)
        
        self.tool_manager = ToolManager(self.config, self.mcp)
        self.planner = System2Planner(
            system2_client=self.client,
            config=self.config,
            memory=self.memory,
            tool_manager=self.tool_manager
        )

    async def shutdown(self):
        if self.mcp:
            await self.mcp.shutdown()

    def reset(self) -> str:
        self.memory.reset()
        self.last_usage = {}
        return "🗑 Conversation history cleared."

    def get_last_usage(self) -> dict:
        return dict(self.last_usage)

    # ─────────────────────────────────────────────
    # TOKEN OPTIMIZATION: TOOL PRUNING
    # ─────────────────────────────────────────────
    def _get_optimized_tools(self, suggested_tools: list = None) -> list:
        """
        Reduces input tokens by pruning tools. 
        Prioritizes suggested_tools from System 1, otherwise uses basic pruning.
        """
        if not self.tools:
            return []

        if suggested_tools:
            # Filter suggested tools to ensure they actually exist in our registry
            filtered = [t for t in self.tools if t["function"]["name"] in suggested_tools]
            # Ensure essential tools are always there
            essential = {"read_file", "list_folder", "search_project", "run_shell_command"}
            for t in self.tools:
                if t["function"]["name"] in essential and t not in filtered:
                    filtered.append(t)
            return filtered

        # Default pruning if no suggestions
        essential = {"read_file", "list_folder", "search_project", "run_shell_command"}
        return [t for t in self.tools if t["function"]["name"] in essential]

    async def handle_message(self, user_input: str) -> AsyncGenerator[str, None]:
        cleaned_input = user_input.strip()
        if not cleaned_input:
            return

        if cleaned_input == "/reset":
            yield self.reset()
            return

        self.memory.append_user(user_input)

        # --- STEP 1: System 1 Dynamic Routing & Reflexive Resolution ---
        # S1 is optimized internally to return a small set of suggested tools
        decision, fast_result, suggested_tools = await self.system1.execute(
            cleaned_input, 
            history=self.memory.get_messages(),
            all_tools=[t["function"]["name"] for t in self.tools]
        )
        
        if decision == "DIRECT_TOOL":
            yield "\x00SYSTEM_PATH:FAST_PATH"
            if fast_result:
                yield fast_result
            return

        if decision == "SIMPLE" and fast_result:
            yield "\x00SYSTEM_PATH:SIMPLE"
            yield fast_result
            return

        if decision == "SIMPLE":
            yield "\x00SYSTEM_PATH:SIMPLE"
        else:
            yield "\x00SYSTEM_PATH:COMPLEX"

        # --- STEP 2: System 2 Execution ---
        if not self.planner:
            await self.initialize()

        # Dynamic Tool Pruning: Use optimized tool set (S1 suggestions + Essentials)
        active_tools = self._get_optimized_tools(suggested_tools)

        queue = asyncio.Queue()
        async def enqueue(text: str):
            await queue.put(text)

        planner_task = asyncio.create_task(
            self.planner.execute(active_tools, enqueue)
        )

        while not planner_task.done() or not queue.empty():
            try:
                result = await asyncio.wait_for(queue.get(), timeout=0.1)
                yield result
            except asyncio.TimeoutError:
                continue

        await planner_task