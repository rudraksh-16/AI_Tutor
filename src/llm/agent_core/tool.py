import asyncio
from typing import Any, Callable, Optional, Type


class Tool:
    def __init__(self, func: Callable[..., Any], description: Optional[str] = None, args_schema: Optional[Any] = None) -> None:
        self.name = func.__name__
        self.func = func
        self.description = description
        self.args_schema = args_schema

    async def execute(self, **kwargs: Any) -> Any:
        if asyncio.iscoroutinefunction(self.func):
            return await self.func(**kwargs)
        return self.func(**kwargs)

    def schema(self) -> dict:
        """Generate the JSON schema for LLM tool selection."""
        schema = {
            "type": "function",
            "name": self.name,
            "description": self.description,
            "parameters": {"type": "object", "properties": {}, "required": []},
        }
        if self.args_schema:
            self._populate_parameters(schema["parameters"])
        return schema

    def _populate_parameters(self, parameters: dict) -> None:
        """Map the internal args_schema to the JSON parameters object."""
        for name, args in self.args_schema.args:
            parameters["properties"][name] = self._build_arg_schema(args)
            if getattr(args, "required", False):
                parameters["required"].append(name)

    def _build_arg_schema(self, args: Any) -> dict:
        """Build the individual field schema for a tool argument."""
        field = {
            "type": self._map_type(args.type),
            "description": args.description,
        }
        if getattr(args, "enum", None):
            field["enum"] = args.enum
        if getattr(args, "default", None) is not None:
            field["default"] = args.default
        return field

    @staticmethod
    def _map_type(py_type: Type[Any]) -> str:
        return {
            int: "integer",
            float: "number",
            str: "string",
            bool: "boolean",
        }.get(py_type, "string")
