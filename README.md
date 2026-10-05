# City Prism

The City AI Readiness Agent for City Holdings. It checks each GenAI project on
8 dimensions (40 questions). The weakest dimension decides the verdict.
Fixed rules set the score and verdict. AI only helps people answer and write.

- Spec: [docs/SPEC.md](docs/SPEC.md)
- Build plan: [docs/BUILD_PLAN.md](docs/BUILD_PLAN.md)

## Run locally

### With Docker (closest to production)

```sh
cp .env.example .env      # optional in dev
docker compose up --build
```

Open http://localhost:8080. On first start the app creates the database,
runs migrations and loads the 40 questions and the 12 projects.
One container serves both the screens and `/api`.

### For development

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
sign-in is off until the company SSO is connected (see below).

## Environment variables

Put them in `.env` (see `.env.example`). Never commit `.env`.

| Variable                  | Default        | What it does                                                                                                              |
| ------------------------- | -------------- | ------------------------------------------------------------------------------------------------------------------------- |
| `ENV`                     | `dev`          | `dev`, `test` or `prod`. With `prod` the test sign-in is off and `SECRET_KEY` is required.                                |
| `SECRET_KEY`              | dev value      | Signs the session cookie. Use a long random value in prod: `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `SESSION_MAX_AGE`         | `43200`        | Seconds a sign-in lasts (12 hours).                                                                                       |
| `DATA_DIR`                | `backend/data` | Folder for the SQLite database. In Docker: `/app/backend/data`.                                                           |
| `DATABASE_URL`            | empty          | Empty means SQLite in `DATA_DIR`. Set a PostgreSQL URL to switch (see below).                                             |
| `FRONTEND_BUILD_DIR`      | `build`        | Where the built screens are. Set in the Docker image.                                                                     |
| `RUN_MIGRATIONS_ON_START` | `true`         | Bring the database up to date when the app starts.                                                                        |
| `SEED_ON_START`           | `true`         | Load the questions, the admin and the 12 projects if they are missing. Existing data is never changed.                    |
| `OPENROUTER_API_KEY`      | empty          | Key for the AI. It stays on the server. Without it the agent says the AI is not set up yet.                               |
| `OPENROUTER_BASE_URL`     | OpenRouter     | Change only for a proxy or for tests.                                                                                     |
| `LLM_MODEL_FAST`          | empty          | Model for the Interview.                                                                                                  |
| `LLM_MODEL_DEFAULT`       | empty          | Model for Read evidence, the decision brief and the portfolio summary.                                                    |
| `LLM_TIMEOUT_SECONDS`     | `60`           | Seconds before an AI call gives up. There is no automatic retry.                                                          |

## Backup and restore

All data is in one folder: `DATA_DIR` (in Docker, the `prism-data` volume at
`/app/backend/data`). Evidence files are stored as text inside the database.

- **Back up:** stop the app (or make sure nobody is saving), then copy the folder.

  ```sh
  docker compose stop
  docker run --rm -v city-prism_prism-data:/data -v "$PWD":/backup alpine \
    tar czf /backup/prism-$(date +%F).tar.gz -C /data .
  docker compose start
  ```

  Check the volume name with `docker volume ls`.

- **Restore:** stop the app, put the copied files back in the folder, start the app.
- Run one copy of the app only (SQLite). Do not put the folder on network
  storage such as EFS.

Nothing is deleted in the app: projects are archived, and every answer change
stays in the history.

## Switch to PostgreSQL

Decide before go-live. The app does not move data between databases for you.

1. Add the driver to `backend/requirements.txt`: `psycopg[binary]>=3.2,<4`, and rebuild.
2. Create an empty database and set
   `DATABASE_URL=postgresql+psycopg://user:password@host:5432/prism`.
3. Start the app. Migrations create the tables and the seed loads the questions,
   the admin and the 12 projects.
4. To keep data from SQLite, copy it table by table before people start using
   the new database (for example with `pgloader`), then check the portfolio
   shows the same verdicts.

The app has only been tested on SQLite so far. Run the server tests against
PostgreSQL once (`DATABASE_URL=... .venv/bin/pytest`) before switching.

## Plug in the company SSO

Sign-in goes through one small interface in `backend/app/auth/provider.py`:

- `options(db)` tells the sign-in screen what to show.
- `authenticate(db, payload)` returns the signed-in `User`, or `None`.

Today `DevSSOProvider` (pick a test user) runs in dev, and `NoProvider` (nobody
can sign in) runs with `ENV=prod`. To connect the company SSO:

1. Add a provider class, for example `OidcProvider`, that checks the token or
   code from the identity provider and finds the user by email. Create the user
   as a project owner the first time they sign in, if that is the policy.
2. Return it from `get_provider()` when `ENV=prod`. Put its client ID, secret and
   issuer URL in environment variables, never in code.
3. If the identity provider needs a redirect, add the callback route in
   `backend/app/routers/auth.py` and call `set_session(response, user.id)` there.
   The rest of the app only reads the session cookie, so nothing else changes.
4. Give the first admins their role in Admin → Users and roles.

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

## Screens

The screens work from phone width (390 px) up, and in light and dark themes.
Each person picks Light, Dark or Follow the system in the menu under their
name; the choice is kept in that browser.

## Export

Admins can download the portfolio from the Export menu:
`GET /api/export.xlsx` (sheets "Answers" and "Portfolio") or `GET /api/export.csv`.
Text that starts with `=`, `+`, `-` or `@` is never run as a formula.

## Checks

```sh
cd backend && .venv/bin/pytest && .venv/bin/ruff check . && .venv/bin/ruff format --check .
npm test && npm run check && npm run lint && npm run build
npm run test:e2e     # browser tests; needs the build and backend/.venv
```

The browser tests (`e2e/`) run the main path (sign in → new project → answer →
interview → evidence → brief → approve → export) at desktop and phone width,
check both themes, and run automated accessibility checks on every screen.
They start the app on a fresh database with a fake OpenRouter
(`e2e/fake_openrouter.py`), so no key or internet is needed.

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
