from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class QuizFeedbackItem(BaseModel):
    question_id: str
    selected_option: Optional[str] = None
    correct_answer: Optional[str] = None
    explanation: Optional[str] = None
    is_correct: bool


class QuizStatePayload(BaseModel):
    quiz_key: str
    selected_answers: Dict[str, str] = Field(default_factory=dict)
    submitted: bool = False
    score: Optional[int] = None
    total: Optional[int] = None
    passed: Optional[bool] = None
    feedback: List[QuizFeedbackItem] = Field(default_factory=list)


class QuizStateResponse(BaseModel):
    quiz_key: str
    selected_answers: Dict[str, str] = Field(default_factory=dict)
    submitted: bool = False
    score: Optional[int] = None
    total: Optional[int] = None
    passed: Optional[bool] = None
    feedback: List[QuizFeedbackItem] = Field(default_factory=list)
    chapter_status: Optional[str] = None
    saved_at: Optional[str] = None

