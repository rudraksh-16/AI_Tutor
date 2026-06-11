import logging
import json

from src.llm.deep_research.state import ResearchState
from src.llm.deep_research.prompt import (
    QUERY_MAKER_SYSTEM_PROMPT,
    QUERY_MAKER_USER_PROMPT,
)
from src.llm.agent_core.agent import Agent
from src.llm.deep_research.constant import DeepResearchConstants

logger = logging.getLogger(__name__)


class QueryMaker(Agent):
    def __init__(
        self,
        state: ResearchState,
        model: str = DeepResearchConstants.DEFAULT_MODEL,
        temperature: float = DeepResearchConstants.DEFAULT_TEMPERATURE,
        max_iteration: int = DeepResearchConstants.DEFAULT_MAX_RETRIES,
    ) -> None:
        self.state = state
        logger.info("Initializing QueryMaker Agent")

        super().__init__(
            system_prompt=QUERY_MAKER_SYSTEM_PROMPT,
            user_prompt=QUERY_MAKER_USER_PROMPT.format(
                query=state["query"], extra=state.get("extra") or "NULL"
            ),
            model=model,
            temperature=temperature,
            max_iteration=max_iteration,
        )
        logger.info("PlannerAgent initialized successfully")


def query_node(state: ResearchState) -> ResearchState:

    query_agent = QueryMaker(
        state=state,
        model=DeepResearchConstants.MODEL,
        temperature=DeepResearchConstants.TEMPERATURE,
        max_iteration=DeepResearchConstants.MAX_RETRIES,
    )
    logger.info("QueryMaker Agent object created sucessfully")
    chat_history = []
    ai_response, _ = query_agent.invoke(chat_history)
    logger.info("QueryMaker Agent invoke completed sucessfully")
    logger.info("Generated response %s", ai_response)
    try:
        plan = json.loads(ai_response)
    except json.JSONDecodeError:
        logger.exception("Reviewer returned invalid JSON")
        return state
    state["subtopics"] = plan["subtopics"]
    state["success_criteria"] = plan["success_criteria"]
    state["current_subtopic"] = plan["subtopics"][0]
    return state
