import logging

from src.llm.deep_research.state import ResearchState
from src.llm.deep_research.prompt import SYNTHESIS_SYSTEM_PROMPT, SYNTHESIS_USER_PROMPT
from src.llm.deep_research.constant import DeepResearchConstants
from src.llm.agent_core.agent import Agent

logger = logging.getLogger(__name__)


class Synthesizer(Agent):
    def __init__(
        self,
        state: ResearchState,
        model: str = DeepResearchConstants.DEFAULT_MODEL,
        temperature: float = DeepResearchConstants.DEFAULT_TEMPERATURE,
        max_iteration: int = DeepResearchConstants.DEFAULT_MAX_RETRIES,
    ) -> None:
        self.state = state
        logger.info("Initializing Synthesizer Agent")

        super().__init__(
            system_prompt=SYNTHESIS_SYSTEM_PROMPT,
            user_prompt=SYNTHESIS_USER_PROMPT.format(
                query=state["query"],
                subtopics=state["subtopics"],
                critique=state.get("critique", []),
                missing=state.get("missing", []),
                scratchpad=state["scratchpad"],
                sources=state["sources"],
            ),
            model=model,
            temperature=temperature,
            max_iteration=max_iteration,
        )
        logger.info("Synthesizer Agent initialized successfully")


def synthesizer_node(state: ResearchState) -> ResearchState:
    synthesizer_agent = Synthesizer(
        state=state,
        model=DeepResearchConstants.MODEL,
        temperature=DeepResearchConstants.TEMPERATURE,
        max_iteration=DeepResearchConstants.MAX_RETRIES,
    )
    logger.info("Synthesizer Agent object created sucessfully")
    chat_history = []
    ai_response, _ = synthesizer_agent.invoke(chat_history)
    logger.info("Synthesizer Agent invoke completed sucessfully")
    state["draft"] = ai_response
    return state
