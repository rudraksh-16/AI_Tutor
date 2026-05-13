import json
import logging
from typing import List, Optional, Any, Tuple, Dict

from openai import OpenAI, AsyncOpenAI

from src.llm.agent_core.constant import Constants
from src.llm.agent_core.tool import Tool
from src.llm.config import LLMConfig

logger = logging.getLogger(__name__)


class Agent:

    def __init__(
        self,
        system_prompt: str,
        user_prompt: Optional[str] = None,
        model: str = Constants.DEFAULT_MODEL,
        temperature: float = Constants.DEFAULT_TEMPERATURE,
        max_iteration: int = Constants.DEFAULT_MAX_ITERATION,
        max_tool_call: int = Constants.DEFAULT_MAX_TOOL_CALLS,
    ):
        self.client = OpenAI(api_key=LLMConfig.OPENAI_API_KEY)
        self.client_async = AsyncOpenAI(api_key=LLMConfig.OPENAI_API_KEY)
        self.system_prompt = system_prompt
        self.user_prompt = user_prompt
        self.model = model
        self.temperature = temperature
        self.max_iteration = max_iteration
        self.max_tool_call = max_tool_call
        self.tools = {}

    def add_tool(self, tool: Tool):
        self.tools[tool.name] = tool

    def on_tool_result(self, tool_name: str, args: dict, result: dict):
        pass

    async def _execute_tool(self, name: str, args: Optional[dict]):
        """Execute a tool with error handling for LLM feedback."""
        try:
            if args:
                return await self.tools[name].execute(**args)
            return await self.tools[name].execute()
        except Exception as e:
            logger.error("Agent %s: Tool execution failed: %s", self.__class__.__name__, e)
            return {"status": "error", "message": f"{type(e).__name__}: {str(e)}"}

    def _call_llm(self, chat_history: List[dict], stream: bool = False):
        return self.client.responses.create(
            model=self.model,
            temperature=self.temperature,
            input=chat_history,
            tools=[tool.schema() for tool in self.tools.values()],
            tool_choice="auto",
            stream=stream,
        )

    def _format_chat_history(self, chat_history: list[dict]) -> List[dict]:
        history = [
            {"role": "system", "content": self.system_prompt},
        ]
        
        # If an initial user prompt was provided, and the chat history is empty, 
        # prepend it as the first user message.
        if self.user_prompt and not chat_history:
             history.append({"role": "user", "content": self.user_prompt})

        if isinstance(chat_history, list):
            history.extend(chat_history)
        else:
            history.append(chat_history)

        return history

    async def invoke(self, chat_history=None):
        """Synchronous-like execution of the agent (no streaming delta events)."""
        chat_history = self._format_chat_history(chat_history or [])
        tool_calls = []

        for _ in range(self.max_iteration):
            response = self._call_llm(chat_history)
            text, new_calls = await self._process_invoke_items(response.output, chat_history)
            tool_calls.extend(new_calls)

            if text:
                logger.debug("Agent %s: LLM Response: %s", self.__class__.__name__, text)
                return text, tool_calls

        logger.warning("Agent %s: Max iterations reached.", self.__class__.__name__)
        return Constants.ERROR_GENERIC, tool_calls

    async def _process_invoke_items(self, items: List[Any], history: List[Dict[str, Any]]) -> Tuple[str, list]:
        """Process output items from a non-streaming LLM call."""
        assistant_text = ""
        tool_calls = []
        for item in items:
            if item.type == "function_call":
                tc = await self._handle_invoke_tool_call(item, history)
                tool_calls.append(tc)
            elif item.type == "message":
                assistant_text += "".join(p.text for p in item.content if p.type == "output_text")
        return assistant_text, tool_calls

    async def _handle_invoke_tool_call(self, item: Any, history: list) -> dict:
        """Execute a single tool call discovered during an invoke session."""
        name = item.name
        args = json.loads(item.arguments) if item.arguments else {}
        
        tool_input = {"type": "function_call", "name": name, 
                      "arguments": json.dumps(args), "call_id": item.call_id}
        history.append(tool_input)

        result = await self._execute_tool(name, args)
        self.on_tool_result(name, args, result)

        tool_output = {"type": "function_call_output", "call_id": item.call_id, 
                       "output": json.dumps(result)}
        history.append(tool_output)
        
        return {"input": tool_input, "output": tool_output}

    async def astream(self, chat_history):
        chat_history = self._format_chat_history(chat_history or [])
        state = {"final_text": "", "tool_calls": [], "current_tool": None, "tool_args_buffer": ""}

        for _ in range(self.max_iteration):
            if state["final_text"] or len(state["tool_calls"]) >= self.max_tool_call:
                break

            stream = await self._call_llm_async(chat_history=chat_history, stream=True)
            async for event in stream:
                async for chunk in self._dispatch_event(event, state, chat_history):
                    yield chunk

    async def _dispatch_event(self, event, state, chat_history):
        """Dispatch stream events to specific handlers."""
        if event.type == "response.output_text.delta":
            yield self._handle_text_delta(event, state)
        elif event.type == "response.output_item.added":
            self._handle_item_added(event, state)
        elif event.type == "response.function_call_arguments.delta":
            self._handle_args_delta(event, state)
        elif event.type == "response.function_call_arguments.done":
            async for chunk in self._handle_args_done(state, chat_history):
                yield chunk
        elif event.type == "response.completed":
            yield self._handle_completed(state)

    def _handle_text_delta(self, event, state):
        state["final_text"] += event.delta
        return {"type": "text", "content": event.delta}

    def _handle_item_added(self, event, state):
        if getattr(event.item, "type", None) == "function_call":
            state["current_tool"] = {"name": event.item.name, "call_id": event.item.call_id}
            state["tool_args_buffer"] = ""

    def _handle_args_delta(self, event, state):
        state["tool_args_buffer"] += event.delta or ""

    async def _handle_args_done(self, state, chat_history):
        current_tool = state["current_tool"]
        args = json.loads(state["tool_args_buffer"] or "{}")
        
        logger.info("Agent %s: Calling tool: %s with args: %s", self.__class__.__name__, current_tool["name"], args)
        result = await self._execute_tool(current_tool["name"], args)
        self.on_tool_result(current_tool["name"], args, result)

        tool_input = {"type": "function_call", "name": current_tool["name"], 
                      "arguments": state["tool_args_buffer"] or "{}", "call_id": current_tool["call_id"]}
        tool_output = {"type": "function_call_output", "call_id": current_tool["call_id"], 
                       "output": json.dumps(result)}

        chat_history.extend([tool_input, tool_output])
        state["tool_calls"].append({"input": tool_input, "output": tool_output})
        
        yield {"type": "tool_call", "data": state["tool_calls"][-1]}
        state["current_tool"] = None
        state["tool_args_buffer"] = ""

    def _handle_completed(self, state):
        return {
            "type": "final",
            "data": {"assistant_text": state["final_text"], "tool_calls": state["tool_calls"]}
        }

    async def _call_llm_async(self, chat_history: List[dict], stream: bool = False):
        return await self.client_async.responses.create(
            model=self.model,
            temperature=self.temperature,
            input=chat_history,
            tools=[tool.schema() for tool in self.tools.values()],
            tool_choice="auto",
            stream=stream,
        )

