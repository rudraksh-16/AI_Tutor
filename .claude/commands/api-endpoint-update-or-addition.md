---
name: api-endpoint-update-or-addition
description: Workflow command scaffold for api-endpoint-update-or-addition in AI_Tutor.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /api-endpoint-update-or-addition

Use this workflow when working on **api-endpoint-update-or-addition** in `AI_Tutor`.

## Goal

Updating or adding API endpoints, often involving changes to multiple endpoint files and related schemas or repositories.

## Common Files

- `src/backend/api/v1/endpoints/*.py`
- `src/backend/repository/*.py`
- `src/backend/services/*.py`
- `src/backend/schemas/*.py`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Modify or create one or more files in src/backend/api/v1/endpoints/
- Update related repository or service files (e.g., src/backend/repository/...)
- Optionally update schemas in src/backend/schemas/ or related directories

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.