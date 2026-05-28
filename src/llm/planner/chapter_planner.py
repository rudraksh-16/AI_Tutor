import json
import logging
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import UUID

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.db.database import SessionLocal
from src.backend.common.exceptions import AlreadyExistsError
from src.backend.planner.repository import planner_repo
from src.llm.config import LLMConfig
from src.llm.planner.constant import PlannerConstants
from src.llm.planner.prompt import SYSTEM_PROMPT, USER_PROMPT

logger = logging.getLogger(__name__)


class Planner:
    """Generates detailed teaching plans for curriculum chapters."""

    def __init__(
        self,
        topic_id: str,
        model: str = PlannerConstants.DEFAULT_MODEL,
        temperature: float = PlannerConstants.DEFAULT_TEMPERATURE,
        max_retries: int = PlannerConstants.DEFAULT_MAX_RETRIES,
    ) -> None:
        self.client = AsyncOpenAI(api_key=LLMConfig.OPENAI_API_KEY)
        self.topic_id = topic_id
        self.model = model
        self.temperature = temperature
        self.max_retries = max_retries

    async def _call_llm(self, messages: List[Dict[str, str]]) -> str:
        """Call LLM with given messages.

        Args:
            messages: List of message dictionaries.

        Returns:
            The string content of the response.
        """
        response = await self.client.chat.completions.create(
            model=self.model, messages=messages, temperature=self.temperature
        )
        return response.choices[0].message.content or ""

    @staticmethod
    async def get_chapters(db: AsyncSession, topic_id: str) -> List[Any]:
        """Fetch all chapters for a given topic ID via Repository layer."""
        return await planner_repo.get_chapters_for_topic(db, topic_id)

    @staticmethod
    async def save_plan(
        db: AsyncSession,
        chapter_id: str,
        plan: str,
        chapter_title: str,
        chapter_order_index: int,
    ) -> Dict[str, str]:
        """Orchestrate saving a generated plan with existence checks via Repository."""
        chapter_uuid = UUID(chapter_id)
        if await planner_repo.plan_exists(db, chapter_uuid):
            logger.info("Plan for chapter %s already exists, skipping.", chapter_title)
            raise AlreadyExistsError(f"Plan already exists for chapter: {chapter_title}")

        try:
            await planner_repo.insert_plan(db, chapter_uuid, plan, chapter_title, chapter_order_index)
            return {"status": "success", "message": "plan saved successfully"}
        except Exception as e:
            logger.error("Failed to save plan for %s: %s", chapter_title, e)
            await db.rollback()
            raise

    def _get_planning_context(self, chapters: List[Any]) -> Dict[str, Any]:
        """Extract user summary, formatted chapter list, and IDs from DB rows.

        Args:
            chapters: List of chapter objects.

        Returns:
            A dictionary containing shared context for prompt formatting.
        """
        if not chapters:
            raise ValueError("No chapters found to build context.")

        user_summary = chapters[0].user_summary
        all_chapters_text = "\n".join(f"- {c.chapter_title}" for c in chapters)
        all_chapter_ids = {c.chapter_id for c in chapters}

        return {
            "user_summary": user_summary,
            "all_chapters_text": all_chapters_text,
            "all_chapter_ids": all_chapter_ids,
        }

    async def _generate_chapter(self, ch: Any, context: Dict[str, Any]) -> str:
        """Construct prompt and generate plan content for one chapter."""
        messages = self._format_chapter_prompt(ch, context)
        
        logger.debug("Prompt for %s: %s", ch.chapter_title, json.dumps(messages, indent=2))
        content = await self._call_llm(messages)

        preview = (content[:200] + "...") if len(content) > 200 else content
        logger.info("Received AI response for %s: %s", ch.chapter_title, preview)
        
        return content

    def _format_chapter_prompt(self, ch: Any, context: Dict[str, Any]) -> List[Dict[str, str]]:
        """Format the system and user messages for chapter planning."""
        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": USER_PROMPT.format(
                    topic_title=ch.topic_title,
                    current_chapter_title=ch.chapter_title,
                    chapter_outline=ch.description,
                    user_summary=context["user_summary"],
                    all_chapters=context["all_chapters_text"],
                ),
            },
        ]

    async def _process_chapter(self, db: AsyncSession, ch: Any, context: Dict[str, Any]) -> bool:
        """Generate and save the plan for a single chapter."""
        content = await self._generate_chapter(ch, context)
        try:
            await self.save_plan(
                db, str(ch.chapter_id), content, ch.chapter_title, ch.chapter_order_index
            )
            return True
        except AlreadyExistsError:
            return True

    async def _execute_attempt(
        self,
        db: AsyncSession,
        chapters: List[Any],
        context: Dict[str, Any],
        saved_ids: Set[UUID],
        on_progress: Optional[Callable] = None,
    ) -> bool:
        """Iterate through all chapters and attempt to generate missing plans."""
        for i, ch in enumerate(chapters, 1):
            if ch.chapter_id in saved_ids:
                continue

            logger.info("[%d/%d] Generating plan: %s", i, len(chapters), ch.chapter_title)
            if await self._try_process_chapter(db, ch, context, saved_ids, on_progress):
                continue

        return saved_ids == context["all_chapter_ids"]

    async def _try_process_chapter(
        self,
        db: AsyncSession,
        ch: Any,
        context: Dict[str, Any],
        saved_ids: Set[UUID],
        on_progress: Optional[Callable] = None
    ) -> bool:
        """Helper to process a single chapter and update progress tracking."""
        try:
            if await self._process_chapter(db, ch, context):
                saved_ids.add(ch.chapter_id)
                if on_progress:
                    await on_progress()
                return True
        except Exception as e:
            logger.error("Error generating chapter %s: %s", ch.chapter_title, e)
        return False

    async def invoke(self, on_progress: Optional[Callable] = None) -> None:
        """Orchestrate the planning process for all chapters with retries."""
        async with SessionLocal() as db:
            try:
                logger.info("Planning started for topic: %s", self.topic_id)
                chapters = await self.get_chapters(db, self.topic_id)
                if not chapters:
                    raise ValueError("No chapters found for topic")

                context = self._get_planning_context(chapters)
                saved_ids: Set[UUID] = set()

                if await self._execute_retries(db, chapters, context, saved_ids, on_progress):
                    logger.info("All plans generated successfully for topic %s.", self.topic_id)
                    return

                missing = context["all_chapter_ids"] - saved_ids
                raise RuntimeError(f"Failed to generate plans for chapters: {missing}")

            except Exception as e:
                logger.exception("Final exception in Planner.invoke: %s", e)
                raise

    async def _execute_retries(
        self,
        db: AsyncSession,
        chapters: List[Any],
        context: Dict[str, Any],
        saved_ids: Set[UUID],
        on_progress: Optional[Callable] = None
    ) -> bool:
        """Manage retry logic for chapter generation attempts."""
        for attempt in range(self.max_retries + 1):
            if await self._execute_attempt(db, chapters, context, saved_ids, on_progress):
                return True

            if attempt < self.max_retries:
                logger.warning("Retrying... (Attempt %d/%d)", attempt + 1, self.max_retries)
        
        return False
