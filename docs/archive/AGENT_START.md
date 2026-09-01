# AGENT_START  Kitchen Hub

**Audience:** Agentic coding tool (e.g., Codex)  
**Primary Goal:** Implement the Kitchen Hub MVP per `KITCHEN_HUB_PLAN.md`, then extend via ROADMAP.  
**Operating Mode:** Deterministic, incremental commits, ask-forgiveness on missing env (use stubs).

## Directives
1. Read `KITCHEN_HUB_PLAN.md` fully. It is the source of truth for feature scope and acceptance criteria.
2. Scaffold the repository exactly per the **Architecture** section.
3. Implement features **by phase order**, committing at the end of each phase with clear messages.
4. Never hardcode secrets. Read `.env` or `instance/`-scoped files only.
5. Favor server-rendered + HTMX partials over SPA patterns. No client bundlers.
6. Implement robust error banners, logging, and cache TTLs before shipping a phase.
7. Keep functions small, typed where helpful, and covered by tests introduced per phase.

## Deliverables
- A runnable Flask app (`flask run` works) with kiosk service files.
- Passing tests for services and HTMX partial routes.
- Minimal but clear CSS with large click targets and dark/light theme.
- Docs updated: `README.md`, `RUNBOOK.md`, `DEPLOYMENT.md`, `TEST_PLAN.md`.

## Commit Discipline
- One feature per commit.
- Message format: `phase-N: short change description`.
- Keep diffs under 400 lines when possible; split if larger.

## Ask-Policy
- If a provider key is missing, implement adapter with mocks and mark TODO in `RUNBOOK.md` under Secrets.

## Success Criteria (MVP)
See `KITCHEN_HUB_PLAN.md`  **Definition of Done (MVP)**.