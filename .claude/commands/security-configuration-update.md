---
name: security-configuration-update
description: Workflow command scaffold for security-configuration-update in AI_Tutor.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /security-configuration-update

Use this workflow when working on **security-configuration-update** in `AI_Tutor`.

## Goal

Making security-related changes, such as updating JWT secret handling, authentication logic, or environment variable requirements.

## Common Files

- `src/backend/config.py`
- `src/backend/api/auth/utils.py`
- `.env.sample`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Update configuration files (e.g., src/backend/config.py)
- Modify authentication or utility files (e.g., src/backend/api/auth/utils.py)
- Update documentation or environment sample files (e.g., .env.sample)

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.