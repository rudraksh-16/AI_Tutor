from typing import Any, AsyncGenerator, Callable, Dict, List, Optional

from src.llm.curriculum_agent.agent import CurriculumAgent
from src.llm.curriculum_agent.constant import CurriculumConstants
from src.llm.curriculum_agent.tools.upsert_curriculum import make_upsert_curriculum_tool
from src.llm.curriculum_agent.tools.get_curriculum import make_get_curriculum_tool
from src.llm.curriculum_agent.tools.web_search import make_web_search_tool
from src.llm.teacher_agent.agent import TeacherAgent
from src.llm.teacher_agent.constant import TeacherConstants
from src.llm.planner.chapter_planner import Planner
from src.llm.planner.constant import PlannerConstants


async def run_curriculum_agent(
    user_id: str,
    topic_id: str,
    chat_history: List[Dict[str, Any]],
) -> AsyncGenerator[Dict[str, Any], None]:
    """Build and stream a CurriculumAgent for the given topic."""
    agent = CurriculumAgent(
        user_id=user_id,
        topic_id=topic_id,
        model=CurriculumConstants.MODEL,
        temperature=CurriculumConstants.TEMPERATURE,
        max_iteration=CurriculumConstants.MAX_ITERATION,
    )
    agent.add_tool(make_upsert_curriculum_tool(user_id, topic_id))
    agent.add_tool(make_get_curriculum_tool(topic_id))
    agent.add_tool(make_web_search_tool())
    async for event in agent.astream(chat_history):
        yield event


async def run_planner(
    topic_id: str,
    on_progress: Optional[Callable] = None,
) -> None:
    """Run the chapter planner for a topic, optionally reporting progress via callback."""
    planner = Planner(
        topic_id=topic_id,
        temperature=PlannerConstants.TEMPERATURE,
        model=PlannerConstants.MODEL,
        max_retries=PlannerConstants.MAX_RETRIES,
    )
    await planner.invoke(on_progress=on_progress)


async def run_teacher_agent(
    chapter_id: str,
    chat_history: List[Dict[str, Any]],
) -> AsyncGenerator[Dict[str, Any], None]:
    """Create and stream a TeacherAgent. chat_history already contains user message."""
    agent = TeacherAgent(
        chapter_id=chapter_id,
        model=TeacherConstants.MODEL,
        max_iteration=TeacherConstants.MAX_ITERATION,
        temperature=TeacherConstants.TEMPERATURE,
    )
    async for event in agent.run(chat_history=chat_history):
        yield event
