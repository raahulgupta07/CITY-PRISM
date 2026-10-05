# City Prism

The City AI Readiness Agent for City Holdings. It checks each GenAI project on
8 dimensions (40 questions). The weakest dimension decides the verdict.
Fixed rules set the score and verdict. AI only helps people answer and write.

- Spec: [docs/SPEC.md](docs/SPEC.md)
- Build plan: [docs/BUILD_PLAN.md](docs/BUILD_PLAN.md)
- Go live on AWS, support and the steering committee pack: [docs/GO_LIVE.md](docs/GO_LIVE.md)

## Run locally

### With Docker (closest to production)

```sh
cp .env.example .env      # optional in dev
docker compose up --build
```

Open http://localhost:8080. On first start the app creates the database,
runs migrations and loads the 40 questions and the 12 projects.
One container serves both the screens and `/api`.

### In GitHub Codespaces (free, nothing to install)

On the repository page: Code → Codespaces → Create codespace. It builds and
starts the app (a few minutes the first time) and opens port 8080 in the
browser. Sign in by picking a test user. Keep the port private: the test
sign-in lets anyone sign in as anyone. Stop the codespace when you are done.

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
sign-in is off; people sign in with the company account (see below).

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
| `PUBLIC_URL`              | empty          | The address people open, e.g. `https://prism.example.com`. Needed for company sign-in.                                    |
| `OIDC_ISSUER`             | empty          | Company sign-in issuer URL. Empty means company sign-in is off.                                                           |
| `OIDC_CLIENT_ID`          | empty          | App (client) ID registered with the identity provider.                                                                    |
| `OIDC_CLIENT_SECRET`      | empty          | Client secret from the identity provider. Keep it in `.env` only.                                                         |
| `OIDC_ALLOWED_DOMAINS`    | empty          | Comma-separated email domains allowed to sign in, e.g. `cityholdings.com.mm`. Empty means any account the issuer accepts. |
| `OIDC_CREATE_USERS`       | `true`         | Create a project owner account the first time a staff member signs in. With `false`, an admin adds people first.          |

## Backup and restore

All data is in one folder: `DATA_DIR` (in Docker, the `prism-data` volume at
`/app/backend/data`). Evidence files are stored as text inside the database.

- **Back up while the app runs:** `python -m app.backup` uses SQLite's online
  backup, checks the copy, and keeps the newest 14 in `DATA_DIR/backups`.

  ```sh
  docker exec city-prism python -m app.backup            # add --keep 30 to keep more
  ```

  These copies sit on the same disk, so also snapshot the disk (on AWS: daily
  EBS snapshots, see [docs/GO_LIVE.md](docs/GO_LIVE.md)) or copy them off the server.

- **Restore:** stop the app, copy the backup over `prism.db` (and delete
  `prism.db-wal` and `prism.db-shm` if they exist), start the app.

  ```sh
  docker compose stop
  docker run --rm -v city-prism_prism-data:/data alpine sh -c \
    'cp /data/backups/prism-20261030-010000.db /data/prism.db && rm -f /data/prism.db-wal /data/prism.db-shm'
  docker compose start
  ```

  Check the volume name with `docker volume ls`.

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

## Company sign-in (SSO)

People sign in with their company account through OpenID Connect (OIDC). This
works with Microsoft Entra ID and any other OIDC identity provider. The browser
only follows redirects; the server swaps the code for a token, checks the
token's signature, issuer, audience, expiry and nonce, and then sets the
session cookie. PKCE and a one-time state guard each sign-in.

1. Register an app with the identity provider (Entra ID: App registrations →
   New registration, single tenant). Add the redirect URI
   `https://<your address>/api/auth/sso/callback` (type Web). Create a client secret.
2. Set in `.env`:

   ```sh
   ENV=prod
   PUBLIC_URL=https://<your address>
   OIDC_ISSUER=https://login.microsoftonline.com/<tenant id>/v2.0
   OIDC_CLIENT_ID=<application (client) id>
   OIDC_CLIENT_SECRET=<client secret value>
   OIDC_ALLOWED_DOMAINS=cityholdings.com.mm
   ```

3. Restart. The sign-in screen shows "Sign in with your company account".
4. The first time someone signs in, they get a project owner account (unless
   `OIDC_CREATE_USERS=false`). People already in Admin → Users and roles keep
   their role; the match is by email. Give approvers and admins their roles there.

The person's email comes from the `email` claim, or from `preferred_username`
or `upn` (Entra ID). Sign-in failures are written to the app log with the reason.
Signing out ends the City Prism session only, not the company account session.

The code is in `backend/app/auth/oidc.py`. `backend/app/auth/provider.py`
picks the provider: company sign-in when `OIDC_ISSUER` is set, the test sign-in
in dev, and nobody in prod without `OIDC_ISSUER`.

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
backend/app/auth/         sign-in providers, company sign-in (OIDC), session cookie, role checks
backend/app/backup.py     online SQLite backup (python -m app.backup)
backend/app/services/     permissions, answer history and undo, file text, export
backend/app/llm/          OpenRouter client and call log, prompts, reply checks
src/lib/scoring.ts        same rules for the screen
src/routes/               screens (SvelteKit, single-page app)
```
