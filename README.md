# City Prism

The City AI Readiness Agent for City Holdings. It checks each GenAI project on
8 dimensions (40 questions). The weakest dimension decides the verdict.
Fixed rules set the score and verdict. AI only helps people answer and write.

- Spec: [docs/SPEC.md](docs/SPEC.md)
- Build plan: [docs/BUILD_PLAN.md](docs/BUILD_PLAN.md)

## Run with Docker

```sh
cp .env.example .env      # optional in dev
docker compose up --build
```

Open http://localhost:8080. On first start the app creates the database,
runs migrations and loads the 40 questions and the 12 projects.

Data lives in one folder, `/app/backend/data` (the `prism-data` volume).
To back up, copy that folder. Run one copy of the app only (SQLite).
Do not put the folder on network storage such as EFS.

## Run for development

Server (port 8080):

```sh
cd backend
uv venv && uv pip install -r requirements-dev.txt   # or python -m venv + pip
.venv/bin/uvicorn app.main:app --reload --port 8080
```

Screens (port 5173, `/api` goes to the server):

```sh
npm install
npm run dev
```

In development you sign in by picking a test user. With `ENV=prod` the test
sign-in is off until the company SSO is connected.

## The AI

The agent calls OpenRouter from the server only. Set `OPENROUTER_API_KEY`,
`LLM_MODEL_FAST` (Interview) and `LLM_MODEL_DEFAULT` (Read evidence, decision
brief, portfolio summary) in `.env`.
Without them the app works, and the agent says the AI is not set up yet.
Every call is logged in the `ai_calls` table (admins: `GET /api/admin/ai-calls`).
Tests use a fake OpenRouter, so they never call a real model.

The decision brief saves the rules result (verdict, scores, weakest link) as a
snapshot first; the AI only writes the headline, summary, actions and risks.
The portfolio summary streams to the screen as server-sent events
(`POST /api/portfolio/summary`); pressing Stop is logged as `stopped`.

## Export

Admins can download the portfolio from the Export menu:
`GET /api/export.xlsx` (sheets "Answers" and "Portfolio") or `GET /api/export.csv`.
Text that starts with `=`, `+`, `-` or `@` is never run as a formula.

## Checks

```sh
cd backend && .venv/bin/pytest && .venv/bin/ruff check . && .venv/bin/ruff format --check .
npm test && npm run check && npm run lint && npm run build
```

`shared/scoring_cases.json` holds the scoring tests from SPEC section 3.4.
pytest and Vitest both run it, so the server and the screen always agree.

## Layout

```
backend/app/scoring.py    scoring rules (source of truth)
backend/app/db/           tables (models.py), engine, migrations runner
backend/alembic/          migrations
backend/app/seed.py       framework, admin, 12 projects (python -m app.seed)
backend/app/auth/         sign-in provider, session cookie, role checks
backend/app/services/     permissions, answer history and undo, file text, export
backend/app/llm/          OpenRouter client and call log, prompts, reply checks
src/lib/scoring.ts        same rules for the screen
src/routes/               screens (SvelteKit, single-page app)
```
