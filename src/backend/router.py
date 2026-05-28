from fastapi import APIRouter

from src.backend.chapters import routes as chapters
from src.backend.conversations import routes as conversations
from src.backend.curriculum import routes as curriculum
from src.backend.quiz import routes as quiz
from src.backend.sidebar import routes as sidebar
from src.backend.teacher import routes as teacher
from src.backend.topics import routes as topics

api_router = APIRouter()

api_router.include_router(sidebar.router, prefix="/sidebar", tags=["sidebar"])
api_router.include_router(topics.router, prefix="/topics", tags=["topics"])
api_router.include_router(chapters.router, prefix="/chapters", tags=["chapters"])
api_router.include_router(conversations.router, prefix="/conversations", tags=["conversations"])

api_router.include_router(curriculum.router, prefix="/chat", tags=["curriculum"])
api_router.include_router(teacher.router, prefix="/chat", tags=["teacher"])
api_router.include_router(quiz.router, prefix="/chat", tags=["quiz"])

