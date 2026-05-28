from typing import Dict, Any
from src.llm.agent_core.agent import Agent
from src.llm.curriculum_agent.prompt import SYSTEM_PROMPT
from src.llm.curriculum_agent.constant import CurriculumConstants


class CurriculumAgent(Agent):
    def __init__(
        self,
        user_id: str,
        topic_id: str,
        model: str = CurriculumConstants.DEFAULT_MODEL,
        temperature: float = CurriculumConstants.DEFAULT_TEMPERATURE,
        max_iteration: int = CurriculumConstants.DEFAULT_MAX_ITERATION,
    ):
        super().__init__(
            system_prompt=SYSTEM_PROMPT,
            model=model,
            temperature=temperature,
            max_iteration=max_iteration,
        )
        self.user_id = user_id
        self.topic_id = topic_id
        self.saved_chapters = set()
        self.save_failures = 0

    def on_tool_result(self, tool_name: str, args: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Track successful curriculum saves to prevent redundant attempts."""
        if tool_name != "upsert_curriculum":
            return
        
        chapter_number = args.get("chapter_number")
        if result.get("status") == "success":
            if chapter_number: 
                self.saved_chapters.add(int(chapter_number))
            self.save_failures = 0
        else:
            self.save_failures += 1

        if self.save_failures > 1:
            raise RuntimeError(CurriculumConstants.ERROR_SAVE_CURRICULUM)
