# City Prism: build plan, phase by phase

City AI Readiness Agent for City Holdings. Source documents: `SPEC.md` v1.0 and `PROMPT-for-Claude-Code.md`.
Deadline: all existing projects assessed by **30 Oct 2026**.
We stop for review at the end of every phase.

---

## Stack (as agreed)

| Layer | Choice |
|---|---|
| Screens | SvelteKit 2 (not 3.0, released 1 Oct 2026) + Svelte 5 + TypeScript, `adapter-static` (single-page app, fallback `index.html`), Tailwind 4, bits-ui |
| Server | Python 3.11, FastAPI, Uvicorn, Pydantic v2 |
| Database | SQLite in `/app/backend/data/prism.db` (WAL mode), SQLAlchemy 2, Alembic. `DATABASE_URL` switches to PostgreSQL |
| AI | OpenRouter through the server only (httpx). `OPENROUTER_API_KEY`, `LLM_MODEL_FAST`, `LLM_MODEL_DEFAULT`, `OPENROUTER_BASE_URL` |
| Files / export | python-docx, pypdf, openpyxl, csv |
| Tests | pytest, Vitest, svelte-check, Playwright |
| Run | One Docker image (Node build stage, then `python:3.11-slim`), port 8080, one volume for data |

Pattern copied from Open WebUI: one container, the FastAPI app serves both `/api` and the built screens.

## Folder layout

```
city-prism/
├─ backend/
│  ├─ app/
│  │  ├─ main.py              FastAPI app, mounts /api and the static build
│  │  ├─ config.py            settings from environment
│  │  ├─ db/                  engine, session, models.py
│  │  ├─ scoring.py           pure rules (source of truth)
│  │  ├─ auth/                AuthProvider interface, DevSSO stub, sessions
│  │  ├─ routers/             one file per area
│  │  ├─ llm/                 client.py, prompts.py, schemas.py, log.py
│  │  ├─ services/            permissions, history, extract_text, export
│  │  ├─ framework.py         the 8 dimensions and 40 questions (seed source)
│  │  └─ seed.py              python -m app.seed
│  ├─ alembic/                migrations
│  └─ tests/
├─ src/                       SvelteKit app
│  ├─ lib/scoring.ts          mirror of scoring.py for instant feedback
│  ├─ lib/api.ts
│  ├─ lib/components/
│  └─ routes/
├─ shared/scoring_cases.json  §3.4 cases, run by pytest AND Vitest
├─ docs/
├─ Dockerfile  docker-compose.yml  .env.example  README.md
```

---

## Phase 0: Decisions (before code)

| # | Decision | Default if no answer |
|---|---|---|
| 0.1 | SvelteKit instead of React | Yes, SvelteKit |
| 0.2 | Hosting: one server with its own disk (SQLite) or RDS PostgreSQL | SQLite on one EC2 / ECS-on-EC2 with EBS. Never on EFS |
| 0.3 | OpenRouter model IDs and base URL | Read from env; placeholders in `.env.example` |
| 0.4 | Dev-only test users (owner, reviewer, approver) | Yes, seeded only when `ENV=dev` |
| 0.5 | `prototype.html` | Build from SPEC + approved mockups until it arrives |
| 0.6 | How an AI answer becomes a person's answer | "Confirm" button, or any edit by a person |
| 0.7 | Phase 2 buttons (Export PDF, Send to steering committee) | Shown disabled, "coming later" |
| 0.8 | Archive action | Admin and reviewer can archive; archived projects hidden by default |

---

## Phase 1: Foundation (6 to 8 Oct)

**Goal:** the app starts in one container, the database holds the framework and the 12 projects, and scoring is proven.

Tasks
1. Repo setup: `backend/` (uv or pip + `pyproject.toml`), SvelteKit app at root, Prettier, ESLint, Ruff, `.editorconfig`, `.gitignore`.
2. `shared/scoring_cases.json` with every case in SPEC §3.4. **Written first.**
3. `backend/app/scoring.py`: `score_dimension(answers)`, `score_project(answers) -> ScoreResult` (dimension scores with `raw` and `capped`, lowest, weakest list, verdict, answered, coverage, partial, band). Pure, no I/O.
4. `src/lib/scoring.ts`: same rules. Vitest runs the same JSON file.
5. SQLAlchemy models for: users, dimensions, questions, projects, answers, answer_history, ai_suggestions, briefs, evidence_files, **ai_calls** (new). Enums as check constraints. Unique (project_id, question_id) on answers.
6. First Alembic migration. App runs `alembic upgrade head` on start.
7. `seed.py`: 8 dimensions, 40 questions (dims 1 and 2 `is_draft = true`), 12 projects from §9 (mode `assess`, due 2026-10-30, owner Rahul Gupta, answers with `source = person`), Rahul Gupta as admin. Idempotent. Test users only in dev.
8. Auth: `AuthProvider` interface; `DevSSOProvider` (pick a seeded user); signed session cookie; `current_user` dependency; `require_role()` helper.
9. FastAPI skeleton: `/api/health`, `/api/me`, `/api/auth/login`, `/api/auth/logout`; serves `/app/build` with SPA fallback.
10. Dockerfile (two stages), `docker-compose.yml` with a named volume, `.env.example`.

Done when
- [x] `docker compose up` serves the app on port 8080 and survives a restart with data kept.
- [x] pytest and Vitest both pass every §3.4 case from the one JSON file.
- [x] Seed gives the expected verdicts: CFC Model and Fresh Replenishment = Fix; 6 = Go; Consumer Insights = Ready (partial); 3 = Not assessed.
- [x] Unit tests for permissions (owner of own project, reviewer all, approver read-only, admin all).

---

## Phase 2: Portfolio and Assess (9 to 14 Oct)

**Goal:** owners can answer all 40 questions by hand, and the portfolio shows the real picture.

Server
1. `GET /api/questions`, `GET /api/users`.
2. `GET /api/projects` with filters `bu, stage, mode, verdict, owner, mine, archived`; returns each project with its computed score. Sorted fix → go → ready → not assessed.
3. `POST /api/projects`, `GET /api/projects/:id` (project + answers + score), `PATCH /api/projects/:id` (stage, owner, sponsor, archive).
4. `PUT /api/projects/:id/answers/:qid` → `{answer, evidence}`; writes `answer_history` in the same transaction; returns the new score. Evidence max 600 characters.
5. `POST /api/projects/:id/answers/:qid/confirm` (turns an `ai_*` answer into a confirmed one).
6. `GET /api/projects/:id/history`.
7. Admin: `GET/PUT /api/admin/questions/:id` (new version on save, draft flag), `GET/PATCH /api/admin/users/:id` (role).

Screens (B + C design)
1. App shell: navy header, theme switch, user menu.
2. Portfolio: headline sentence (from rules, not AI), verdict counts, answered bar, filter rail, score grid table with weakest cell outlined, "Where projects get stuck", footer rule text.
3. New project form → opens Assess.
4. Assess: dark band with the project sentence and the 8 dimension bars as tabs; question rows with the 4-way answer control (click again to clear), evidence field (saves on blur), "Draft wording" note, last changed by and when, history drawer.
5. Admin: question set editor, users and roles.

Done when
- [ ] Portfolio shows all 12 seed projects with correct scores, verdicts and weakest links.
- [ ] An owner can only edit their own projects; a reviewer can edit any; an approver cannot edit.
- [ ] Every change appears in history.
- [ ] Portfolio loads in under 2 s with 200 generated projects (load test script).

---

## Phase 3: The agent (15 to 19 Oct)

**Goal:** the AI helps people answer, and people stay in charge.

Server
1. `llm/client.py`: OpenRouter call with timeout, JSON mode, no automatic retries; writes one `ai_calls` row per call (user, project, feature, model, prompt and completion tokens, cost, latency, ok/error).
2. `llm/prompts.py`: the exact prompts from SPEC §6.2 to §6.5.
3. `llm/schemas.py`: Pydantic models for each reply. Invalid JSON → friendly error, nothing saved.
4. `POST /api/projects/:id/agent/interview` (fast model) → `{answer, evidence, followUp}`. A decided answer is saved with `source = ai_interview`.
5. `POST /api/projects/:id/answers/:qid/undo` reverts the last agent answer; the undo is written to history.
6. `POST /api/projects/:id/agent/evidence` (default model): pasted text or uploaded file (txt, md, csv, docx, pdf); text extracted on the server; at most 24,000 characters sent; file and text kept in `evidence_files`. Drops unknown IDs and invalid answers. Stores `ai_suggestions` as pending (max 15).
7. `POST /api/suggestions/:id/accept`, `/dismiss`, `POST /api/projects/:id/suggestions/accept-all`. Accepted → answer with `source = ai_evidence`.

Screens
1. Agent panel with Interview and Read evidence tabs.
2. Interview: next unanswered question (current dimension first), transcript, "Recorded 5.1: No. …" with Undo, Send (Ctrl/Cmd+Enter), Skip, Stop, follow-up questions.
3. Read evidence: paste box, file upload, suggestion list with Accept / Dismiss / Accept all.
4. "AI suggested, not confirmed" marker and Confirm button on answers.

Done when
- [ ] Tests with a mocked OpenRouter: valid reply, vague reply (follow-up), invalid JSON, unknown question ID.
- [ ] AI answers stay marked until a person confirms or edits them.
- [ ] Undo works for the last agent answer and is in history.
- [ ] Every AI call has a row in `ai_calls`. No AI call from the browser (checked in Playwright).

---

## Phase 4: Decision brief, summary and export (20 to 24 Oct)

**Goal:** the steering committee gets a clear brief and the portfolio can leave the app.

Server
1. `POST /api/projects/:id/briefs`: compute the rules result first, send it with the answers (SPEC §6.4), validate, save the snapshot (verdict, lowest, weakest, dimension scores, answered) with the AI text.
2. `GET /api/projects/:id/briefs` (history, latest first).
3. `POST /api/briefs/:id/approve`, approver role only.
4. `POST /api/portfolio/summary`, streamed (SSE), SPEC §6.5 prompt.
5. `GET /api/export.csv` and `GET /api/export.xlsx`: one row per project × question (SPEC §8 columns); XLSX adds the "Portfolio" sheet.

Screens
1. Decision brief: verdict from rules, "Partial: x of 40" note, weakest link, AI headline and summary (marked as written by AI), 8 score bars, top 3 actions, risks, open-questions note, footer text, version picker, Approve (approvers only), Export PDF and Send (disabled, phase 2).
2. Portfolio summary panel with streaming text, Stop, Copy, Write again.
3. Export menu (CSV, XLSX).

Done when
- [ ] The brief never shows a verdict different from the rules result (test).
- [ ] Only approvers can approve (test).
- [ ] Export columns match SPEC §8; the file opens in Excel.

---

## Phase 5: Phone, dark mode, accessibility, docs (25 to 28 Oct)

1. Phone layout at 390 to 400 px: portfolio as cards, Assess with dimension chips and stacked panels.
2. Dark theme for every screen, plus "follow the system" setting.
3. Accessibility pass: real buttons and labels, keyboard use, visible focus, 44 px targets, 4.5:1 contrast, screen-reader labels on score cells.
4. Copy pass: plain international English everywhere.
5. Playwright tests for the main path: sign in → new project → answer → interview → evidence → brief → approve → export.
6. README: run locally, environment variables, backup (copy the data folder), switch to PostgreSQL, plug in the real SSO.

Done when: every item in SPEC §13 is ticked.

---

## Phase 6: Go live and support (29 to 30 Oct)

1. Deploy to the City AI estate (AWS ap-southeast-1), HTTPS, volume backups.
2. Owners fill in their assessments; fix what they report.
3. Prepare the steering committee pack from the briefs and the portfolio export.

---

## Rules for every phase

- AI never sets a score or a verdict.
- The browser never calls the AI model. Only the minimum text goes to the model.
- Nothing is deleted. Projects are archived.
- Every answer change is in history. Every AI call is logged.
- Plain international English in all screen text.
- No features outside the spec without approval (command bar, board view and project peek are on hold).
