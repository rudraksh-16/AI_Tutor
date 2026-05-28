import logging
import json

from src.llm.agent_core.agent import Agent
from src.llm.deep_research.state import ResearchState
from src.llm.deep_research.constant import DeepResearchConstants
from src.llm.deep_research.prompt import REVIEWER_SYSTEM_PROMPT, REVIEWER_USER_PROMPT

logger = logging.getLogger(__name__)


class Reviewer(Agent):
    def __init__(
        self,
        state: ResearchState,
        model: str = DeepResearchConstants.DEFAULT_MODEL,
        temperature: float = DeepResearchConstants.DEFAULT_TEMPERATURE,
        max_iteration: int = DeepResearchConstants.DEFAULT_MAX_RETRIES,
    ) -> None:
        self.state = state
        logger.info("Initializing Reviewer Agent")

        super().__init__(
            system_prompt=REVIEWER_SYSTEM_PROMPT,
            user_prompt=REVIEWER_USER_PROMPT.format(
                current_subtopic=state["current_subtopic"],
                current_coverage=state.get("covered_subtopics", {}),
                scratchpad=state.get("scratchpad", ""),
                sources=state.get("sources", []),
            ),
            model=model,
            temperature=temperature,
            max_iteration=max_iteration,
        )

        logger.info("Reviewer Agent initialized successfully")


def reviewer_node(state: ResearchState) -> ResearchState:
    """Orchestrate the review process for the current research findings."""
    reviewer = Reviewer(
        state=state,
        model=DeepResearchConstants.MODEL,
        temperature=DeepResearchConstants.TEMPERATURE,
        max_iteration=DeepResearchConstants.MAX_RETRIES,
    )

    ai_response, _ = reviewer.invoke([])
    data = _parse_reviewer_response(ai_response)
    if not data:
        return state

    _apply_reviewer_results(state, data)
    _handle_reviewer_attempts(state)
    
    return state


def _parse_reviewer_response(ai_response: str) -> dict:
    """Safely parse the JSON response from the reviewer agent."""
    try:
        return json.loads(ai_response)
    except json.JSONDecodeError:
        logger.exception("Reviewer returned invalid JSON")
        return {}


def _apply_reviewer_results(state: ResearchState, data: dict) -> None:
    """Update the research state based on reviewer feedback scores."""
    scores = data.get("scores", {})
    final_score = sum(scores.values()) / max(len(scores), 1)
    
    state["scores"] = scores
    state["final_score"] = final_score
    state["approved"] = final_score >= 0.65
    state["critique"] = data.get("critique")
    state["missing"] = data.get("missing")
    state["improvement_instructions"] = data.get("improvement_instructions")

    if state["approved"]:
        state["missing"] = None
        state["improvement_instructions"] = None
    
    logger.info("Review completed | score: %.2f | approved: %s", 
                final_score, state["approved"])


def _handle_reviewer_attempts(state: ResearchState) -> None:
    """Track review attempts and force progress if limit reached."""
    attempts = state.get("reviewer_attempts", 0) + 1
    state["reviewer_attempts"] = attempts
    if attempts >= DeepResearchConstants.MAX_RETRIES:
        state["forced_progress"] = True


def route_after_reviewer(state: ResearchState) -> str:
    if state.get("approved") or state.get("forced_progress"):
        return "set_next_query"
    return "researcher"
