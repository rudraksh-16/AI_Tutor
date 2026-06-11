import json
import os
from typing import Any, Dict, List


def load_json(file_path: str) -> list:
    if not os.path.exists(file_path):
        data = []
    else:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            data = []

    return data


def append_response_json(file_path: str, new_item: Any) -> None:
    """Append one item (or extend with a list) into a JSON file."""
    data = load_json(file_path)
    if isinstance(new_item, list):
        data.extend(new_item)
    else:
        data.append(new_item)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


def extract(tool_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract tool input/output pairs, excluding curriculum-fetch calls."""
    result: List[Dict[str, Any]] = []
    for tool in tool_results:
        if tool["input"]["name"] == "get_user_curriculum_tool":
            continue
        result.append(tool["input"])
        result.append(tool["output"])
    return result


def add_message(final_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Convert agent final_data into an OpenAI-compatible chat history list."""
    chat_history: List[Dict[str, Any]] = []
    tools = extract(final_data["tool_calls"])
    if final_data["assistant_text"].strip():
        assistant = {"role": "assistant", "content": final_data["assistant_text"]}
        tools.append(assistant)
    if isinstance(tools, list):
        chat_history.extend(tools)
    else:
        chat_history.append(tools)
    return chat_history
