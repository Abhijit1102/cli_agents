import re
import asyncio
import anyio
from typing import Any, List, Dict, Optional, Tuple
from cli_agents.v1.core.base import BaseProcess
from typesafe_sdk import Choice, TypeSafeClient
from cli_agents.tools import execute_tool

class DynamicIntentEngine(BaseProcess):
    """
    Truly Dynamic System 1.
    Uses semantic analysis to decide if a request is SIMPLE, COMPLEX, or a DIRECT_TOOL call.
    Also identifies relevant tools to reduce token overhead for System 2.
    """
    def __init__(self, config: Any):
        self.client = TypeSafeClient(api_key=config.jevai_api_key)
        self.config = config
        
        # Absolute fast-path for basic greetings (zero LLM cost)
        self._reflexive_map = getattr(config, "system1_reflexive_map", {
            "hi": ("SIMPLE", None, "Hello! How can I help you today?"),
            "hello": ("SIMPLE", None, "Hi there! I'm ready to help with your project."),
            "hey": ("SIMPLE", None, "Hey! What's on your mind?"),
            "who are you": ("SIMPLE", None, "I am the V1 AI Controller, a dual-process agent designed for efficient coding assistance."),
            "what are you": ("SIMPLE", None, "I'm a coding agent utilizing a System 1 (Fast) and System 2 (Slow) architecture."),
            "help": ("SIMPLE", None, "I can list files, read code, and help you implement features. Try 'ls .' or ask me a complex coding question."),
        })

        # Tools that are safe for System 1 to execute without deep planning
        self._safe_fast_tools = ["list_folder", "get_file_info"]

    async def classify_content(self, content: str, decision_prompt: str) -> str:
        """
        Ad-hoc classification for System 2. 
        Allows System 2 to delegate a decision to System 1.
        """
        try:
            response = self.client.system_one(
                state={
                    "content": content,
                    "instruction": decision_prompt,
                },
                questions={
                    "decision": (
                        "Based on the content and instruction, provide a clear decision or classification. "
                        "Be concise."
                    )
                },
            )
            return response.answers.get("decision", "Unable to classify.")
        except Exception as e:
            return f"Error during System 1 classification: {e}"

    async def _execute_fast_tool(self, tool_name: str, arg_value: str) -> str:
        """Execute a safe tool without System 2 reasoning."""
        try:
            args = {"path": arg_value.strip()}
            result = await anyio.to_thread.run_sync(
                lambda: execute_tool(tool_name, args, self.config)
            )
            return f"\x00FAST_TOOL_RESULT:{tool_name}:{str(result)}"
        except Exception as e:
            return f"\x00ERROR:Fast tool {tool_name} failed: {e}"

    async def execute(self, user_input: str, history: Optional[List[Dict]] = None, all_tools: List[str] = None) -> Tuple[str, Optional[str], List[str]]:
        """
        Determine intent dynamically and suggest relevant tools.
        Returns: (Intent, OptionalResult, SuggestedTools)
        """
        cleaned_input = user_input.lower().strip()

        # --- STAGE 1: Absolute Reflexive (Zero Cost) ---
        if cleaned_input in self._reflexive_map:
            intent, tools, response = self._reflexive_map[cleaned_input]
            return intent, (response if intent == "SIMPLE" else None), (tools or [])

        # --- STAGE 2: Dynamic Semantic Analysis ---
        context = ""
        if history:
            last_msgs = history[-2:]
            context = " ".join([m.get("content", "") for m in last_msgs])

        try:
            # We ask the LLM to perform a 3-way classification, extract arguments, and prune tools
            response = self.client.system_one(
                state={
                    "user_input": user_input,
                    "context": context,
                    "safe_tools": self._safe_fast_tools,
                    "available_tools": all_tools or [],
                    "instruction": (
                        "Classify the user request. "
                        "1. SIMPLE: General conversation or simple questions. "
                        "2. DIRECT_TOOL: A request to perform a safe, single-step action (e.g., listing a folder). "
                        "3. COMPLEX: Requests requiring planning, file editing, or multi-step reasoning."
                    )
                },
                questions={
                    "classification": Choice(
                        instructions="Determine if the request is SIMPLE, DIRECT_TOOL, or COMPLEX.",
                        options=["SIMPLE", "DIRECT_TOOL", "COMPLEX"],
                    ),
                    "tool_name": Choice(
                        instructions="If DIRECT_TOOL, which tool should be used? Otherwise, leave blank.",
                        options=self._safe_fast_tools + ["NONE"],
                    ),
                    "tool_arg": (
                        "Extract the path or argument for the tool. "
                        "If no tool is needed, leave blank."
                    ),
                    "relevant_tools": (
                        "List the names of tools from available_tools that are likely needed for this request. "
                        "Separate by commas. If COMPLEX, suggest 3-7 tools. If unsure, list 'ALL'."
                    )
                },
            )

            classification = response.answers["classification"].choice
            tool_name = response.answers["tool_name"].choice
            tool_arg = response.answers.get("tool_arg", "")
            
            # Process suggested tools
            raw_tools = response.answers.get("relevant_tools", "ALL")
            if raw_tools == "ALL" or not raw_tools:
                suggested_tools = all_tools or []
            else:
                suggested_tools = [t.strip() for t in raw_tools.split(",") if t.strip()]

            if classification == "DIRECT_TOOL" and tool_name != "NONE" and tool_arg:
                result = await self._execute_fast_tool(tool_name, tool_arg)
                return "DIRECT_TOOL", result, suggested_tools

            if classification == "SIMPLE":
                return "SIMPLE", None, suggested_tools

            return "COMPLEX", None, suggested_tools

        except Exception as e:
            # Fallback to COMPLEX and ALL tools to ensure robustness
            return "COMPLEX", None, (all_tools or [])
