import logging.config
import os
from typing import Any, Dict


LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


def configure_logging() -> None:
    """Configure application logging handlers and feature-specific log files."""
    os.makedirs("logs", exist_ok=True)
    logging.config.dictConfig(_build_logging_config())


def _build_logging_config() -> Dict[str, Any]:
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {"format": LOG_FORMAT},
        },
        "handlers": {
            "console": {
                "level": "INFO",
                "class": "logging.StreamHandler",
                "formatter": "standard",
            },
            "app_file": {
                "level": "DEBUG",
                "class": "logging.FileHandler",
                "filename": "logs/app.log",
                "formatter": "standard",
            },
            "planner_file": {
                "level": "DEBUG",
                "class": "logging.FileHandler",
                "filename": "logs/planner.log",
                "formatter": "standard",
            },
            "curriculum_file": {
                "level": "DEBUG",
                "class": "logging.FileHandler",
                "filename": "logs/curriculum.log",
                "formatter": "standard",
            },
            "teacher_file": {
                "level": "DEBUG",
                "class": "logging.FileHandler",
                "filename": "logs/teacher.log",
                "formatter": "standard",
            },
        },
        "loggers": _build_logger_config(),
    }


def _build_logger_config() -> Dict[str, Any]:
    return {
        "": {
            "handlers": ["console", "app_file"],
            "level": "DEBUG",
            "propagate": True,
        },
        "src.llm.planner": _file_logger("planner_file"),
        "src.backend.planner.services": _file_logger("planner_file"),
        "src.llm.curriculum_agent": _file_logger("curriculum_file"),
        "src.backend.curriculum.routes": _file_logger("curriculum_file"),
        "src.llm.teacher_agent": _file_logger("teacher_file"),
        "src.llm.quiz_agent": _file_logger("teacher_file"),
        "src.backend.teacher.routes": _file_logger("teacher_file"),
        "src.backend.quiz.routes": _file_logger("teacher_file"),
        "src.backend.teacher.services": _file_logger("teacher_file"),
        "src.backend.quiz.services": _file_logger("teacher_file"),
    }


def _file_logger(handler_name: str) -> Dict[str, Any]:
    return {
        "handlers": [handler_name],
        "level": "DEBUG",
        "propagate": True,
    }

