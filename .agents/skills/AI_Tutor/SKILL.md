```markdown
# AI_Tutor Development Patterns

> Auto-generated skill from repository analysis

## Overview
This skill teaches you the core development patterns and conventions used in the `AI_Tutor` Python codebase. You'll learn how to structure code, write and organize tests, follow commit and file naming conventions, and execute common workflows such as updating API endpoints, improving security, and enforcing coding standards. This guide is ideal for contributors looking to quickly onboard and maintain consistency across the project.

## Coding Conventions

- **Language:** Python
- **Framework:** None detected (vanilla Python)
- **File Naming:** Use `snake_case` for all file names.
  - Example: `user_service.py`, `auth_utils.py`
- **Import Style:** Use relative imports within modules.
  - Example:
    ```python
    from .models import User
    from ..utils import hash_password
    ```
- **Export Style:** Use named exports; avoid wildcard imports.
  - Example:
    ```python
    def authenticate_user(...):
        ...
    ```
- **Commit Messages:** Follow [Conventional Commits](https://www.conventionalcommits.org/) with these prefixes:
  - `fix`, `feat`, `security`, `docs`, `refactor`, `chore`
  - Example: `feat: add endpoint for user progress tracking`
- **Type Hints:** Add type hints to function signatures and variables.
  - Example:
    ```python
    def get_user_by_id(user_id: int) -> Optional[User]:
        ...
    ```
- **Logging & Exception Handling:** Use standardized logging and consistent exception handling patterns.

## Workflows

### API Endpoint Update or Addition
**Trigger:** When you need to add a new API endpoint or update existing API logic.  
**Command:** `/new-api-endpoint`

1. Modify or create one or more files in `src/backend/api/v1/endpoints/`.
2. Update related repository or service files (e.g., `src/backend/repository/`, `src/backend/services/`).
3. Optionally update schemas in `src/backend/schemas/` or related directories.
4. Ensure all changes are covered by tests and follow coding conventions.
5. Commit with a message like:  
   `feat: add endpoint for lesson completion tracking`

**Example:**
```python
# src/backend/api/v1/endpoints/lesson.py
from ..schemas import LessonCompleteRequest
from ...repository.lesson import mark_lesson_complete

def complete_lesson(request: LessonCompleteRequest):
    return mark_lesson_complete(request.user_id, request.lesson_id)
```

### Security Configuration Update
**Trigger:** When you want to improve or update security configuration or authentication mechanisms.  
**Command:** `/security-update`

1. Update configuration files (e.g., `src/backend/config.py`).
2. Modify authentication or utility files (e.g., `src/backend/api/auth/utils.py`).
3. Update documentation or environment sample files (e.g., `.env.sample`).
4. Review for secure handling of secrets, tokens, and environment variables.
5. Commit with a message like:  
   `security: update JWT secret handling for token validation`

**Example:**
```python
# src/backend/config.py
import os

JWT_SECRET: str = os.getenv("JWT_SECRET", "default_secret")
```

### Coding Regulations Compliance Fix
**Trigger:** When you want to enforce or improve coding standards across the codebase.  
**Command:** `/enforce-coding-standards`

1. Update multiple backend and LLM files to add type hints and standardize code style.
2. Refactor logging and exception handling for consistency.
3. Apply consistent type usage (e.g., `Optional[str]`).
4. Run linters and formatters to ensure compliance.
5. Commit with a message like:  
   `refactor: add type hints and standardize logging across endpoints`

**Example:**
```python
# Before
def get_user(user_id):
    ...

# After
from typing import Optional

def get_user(user_id: int) -> Optional[User]:
    ...
```

## Testing Patterns

- **Test File Naming:** Test files use the pattern `*.test.*` (e.g., `user_service.test.py`).
- **Testing Framework:** Not explicitly detected; use standard Python testing tools (e.g., `unittest`, `pytest`).
- **Test Structure:** Place tests alongside or near the modules they cover.
- **Example Test:**
    ```python
    # user_service.test.py
    from .user_service import get_user

    def test_get_user_returns_none_for_invalid_id():
        assert get_user(-1) is None
    ```

## Commands

| Command                | Purpose                                                   |
|------------------------|-----------------------------------------------------------|
| /new-api-endpoint      | Start the workflow for adding or updating an API endpoint |
| /security-update       | Begin a security configuration or authentication update   |
| /enforce-coding-standards | Apply codebase-wide coding standards and compliance fixes |
```
