# Smart Tourist Management System — Project Control Pack

**Purpose:** Keep one source of truth for scope, sequence, verification, decisions, and project status.

## How we will work
1. Keep this folder as the project planning authority and copy it into the repository under `docs/project-control/`.
2. The existing repository and database determine what is implemented. Old prompts are specifications, not proof of implementation.
3. Follow the order in `PROJECT_PLAN.md`. Do not jump to mobile/dashboard/analytics implementation before the current prerequisite is verified.
4. Use PowerShell commands from the stated working directory. Give one main task at a time and wait for terminal output whenever the next action depends on it.
5. Do not overwrite large files or run destructive database operations without inspection, backup, and explicit approval.
6. A checkbox becomes `[x]` only after a test or direct inspection proves it works. Use `[~]` for partial, `[ ]` for not started, and `[!]` for blocked/decision required.
7. Keep raw datasets unchanged; normalize into separate outputs. Never fabricate incidents, dates, counts, severity, coordinates, or delivery statuses.
8. Clearly label synthetic demo records and unverified geographic boundaries.
9. Keep secrets out of source control and client apps. Protect tourist personal data in logs, screenshots, and reports.
10. Every work session ends with a concise update to `PROJECT_STATUS.md`, `DECISIONS_LOG.md`, and `CHANGELOG.md` when relevant.

## Current checkpoint (from conversation; re-verify against live repo)
- Backend reportedly starts with `python -m uvicorn app.main:app --reload` from `backend`.
- Direct database query showed all nine `College Demo Zone 01`–`09` rows, IDs 201, 203, 205, 210–215, each active, `RESTRICTED`, radius 200 m, with demo disclaimers.
- `GET /zones` returned many `DEMO-KA-*` synthetic records; the pasted response was truncated before confirming whether the nine College Demo Zone records were included. The API-filter check is the next action.
- Six tourist registration records and added registration fields were previously reported imported; do not print private contact details unless necessary.
- These are conversation-reported states, not a substitute for fresh verification.

## Files
- `PROJECT_PLAN.md`: fixed scope and phase order.
- `PROJECT_STATUS.md`: checklist and evidence.
- `NEXT_STEP.md`: one current task only.
- `DATA_SOURCE_INVENTORY.csv`: candidate source inventory; candidates are not claimed downloaded or verified.
- `DECISIONS_LOG.md`: decisions, constraints, unresolved questions.
- `CHANGELOG.md`: verified project changes.
- `ACCEPTANCE_TESTS.md`: end-to-end and feature acceptance criteria.
