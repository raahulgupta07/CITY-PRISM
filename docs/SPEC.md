# City AI Readiness Agent — Build Spec

Version 1.0 · 5 Oct 2026 · Owner: Rahul Gupta, City AI Team, City Holdings

A working prototype exists (`prototype.html`, in this folder). Use it as the reference for the look, behaviour and prompts. This spec turns it into a production app.

---

## 1. Purpose

City Holdings uses the **GenAI Strategy Canvas** as its official tool for:

1. **Planning** every new GenAI project (every agent and every LLM use case) before build starts.
2. **Assessing** every existing GenAI project. All existing projects must be assessed by **30 Oct 2026**, then reassessed every quarter.

The app checks each project on 8 dimensions (40 yes/no-style questions). The **weakest dimension decides** whether the project is ready. AI helps people answer and writes the decision brief, but **fixed rules, not AI, decide the score and verdict**.

## 2. Users and roles

| Role | Who | Can do |
|---|---|---|
| Project owner | Anyone who runs a GenAI project | Create projects, answer questions for projects they own, use the agent, generate a brief |
| Reviewer | City AI team | Everything a project owner can do, on all projects; edit any answer |
| Approver | Steering Committee members | Read everything; approve a decision brief |
| Admin | City AI team lead | Manage users and roles, edit the question set, export everything |

Everyone in the company can **read** the portfolio. Writing is limited as above.

## 3. The framework (source of truth)

### 3.1 Dimensions and questions

8 dimensions × 5 sub-questions = 40 questions. Question IDs are `<dimension>.<number>` (e.g. `5.1`).

**Dimensions 1 and 2 are DRAFT wording.** Store questions in the database (not hard-coded) so the admin can replace them without a deploy. Mark draft questions with `is_draft = true` and show a "Draft wording" note in the UI.

**1 — Strategy & Priorities** (group: Direction) — DRAFT
Lead: Is this the right use case, and will its value reach the P&L?
- 1.1 Is the business problem and the target outcome clearly stated?
- 1.2 Does the use case support a 2030 aspiration or a stated business priority?
- 1.3 Have we estimated the expected value?
- 1.4 Is this use case a priority compared with other use cases?
- 1.5 Is there a clear path for the benefits to reach the P&L?

**2 — Ownership & Delivery** (group: Foundations) — DRAFT
Lead: Does the application have a clear owner and committed resources to move from idea to sustained operation?
- 2.1 Is there a named business owner?
- 2.2 Are responsibilities clear to the business unit or function?
- 2.3 Does someone have authority to clear bottlenecks?
- 2.4 Have the business unit and IT committed people to it?
- 2.5 Is there a funding plan beyond the pilot?

**3 — Data & Knowledge** (group: Foundations)
Lead: Does the application have access to the required data and business knowledge, and can both remain current?
- 3.1 Have we identified the data, documents and knowledge the application needs?
- 3.2 Can we access these sources, with permission to use them for this use case?
- 3.3 Are the sources accurate, complete, consistent and current enough?
- 3.4 Have we captured the business rules, exceptions and examples that experts use?
- 3.5 Who owns the sources and manages changes to them?

**4 — Technology & Engineering** (group: Foundations)
Lead: Can the team build, integrate, monitor and maintain the application at the required scale and cost?
- 4.1 Can it use a shared GenAI platform and existing components?
- 4.2 Can it connect to the enterprise systems it needs to read from or act within?
- 4.3 Can people use it inside the tools and workflow they already rely on?
- 4.4 Can the team monitor usage, errors and cost in production?
- 4.5 Can models or vendors change without rebuilding the application?

**5 — Quality & Assurance** (group: Adoption)
Lead: Can the team show that the application is good enough and safe enough for its intended use, with the correct fallbacks and human oversight?
- 5.1 Has the business agreed a quality threshold before launch?
- 5.2 Can the team test quality using representative real cases?
- 5.3 Will the team retest after model, prompt or data changes?
- 5.4 Can users verify outputs and see the supporting sources?
- 5.5 Are oversight, escalation and fallback arrangements clear?

**6 — Workflow & Role Redesign** (group: Adoption)
Lead: Has the work been redesigned around the application, with a clear division between people and AI?
- 6.1 Have we mapped the current work, including handoffs, approvals and exceptions?
- 6.2 Which tasks should change rather than simply receive an AI layer?
- 6.3 Which tasks belong to AI, which remain with people, and who decides when AI is uncertain?
- 6.4 Could faster output create a downstream bottleneck?
- 6.5 Do procedures and decision rights reflect the proposed way of working?

**7 — People & Adoption** (group: Adoption)
Lead: Are the people who will use the application able and willing to work with it?
- 7.1 Do users have the skills to use the application and judge its output?
- 7.2 Will practical support be available during early adoption?
- 7.3 Have future users helped shape and test the application?
- 7.4 Do leaders visibly support and use it?
- 7.5 Will the team track meaningful adoption and address the reasons people disengage?

**8 — Value Capture & Improvement** (group: Scale)
Lead: Will the application produce measurable results, tracked against its baseline and total cost?
- 8.1 Have we agreed the baseline and outcome measures?
- 8.2 How will the organisation use any capacity released by the application?
- 8.3 Will the expected benefit appear in the business owner's targets or budget?
- 8.4 Will benefits be tracked against development and running costs?
- 8.5 What routine will improve the application after launch?

### 3.2 Answer scale

Each question gets one answer plus free-text evidence.

| Answer | Points | Meaning |
|---|---|---|
| Yes | 5 | Fully true today |
| Partly | 3 | Partly true or in progress |
| No | 1 | Not true |
| Don't know | 1 | Unknown is treated as a risk |
| (blank) | — | Not answered; excluded from scoring |

### 3.3 Scoring rules (deterministic — never AI)

Implement as a pure, unit-tested function `scoreProject(answers) -> ScoreResult`.

1. **Dimension score** = average points of the answered questions in that dimension. No answers → `null` (not assessed).
2. **No-cap rule:** if any answer in a dimension is `No`, the dimension score is capped at **3.0**. Keep the uncapped value as `raw`.
3. Round dimension scores to 1 decimal.
4. **Lowest** = minimum of the non-null dimension scores.
5. **Weakest link** = every dimension whose score equals the lowest (ties allowed).
6. **Verdict** from the lowest score:
   - no dimension scored → `not_assessed` ("Not assessed")
   - lowest ≤ 2.4 → `fix` ("Fix before next stage")
   - lowest ≤ 3.4 → `go` ("Go with actions")
   - lowest > 3.4 → `ready` ("Ready")
7. **Partial** = fewer than 40 questions answered. Show "(partial)" after the verdict.
8. **Coverage** = answered / 40.

Colour bands for scores: ≤ 2.4 red (weak), ≤ 3.4 amber (partial), > 3.4 green (strong), null grey.

### 3.4 Acceptance tests for scoring

| Answers in one dimension | Expected score |
|---|---|
| Yes, Yes, Yes, Yes, No | raw 4.2 → **3.0** (capped) |
| No | **1.0** |
| Yes, Partly | **4.0** |
| Partly, Partly, Don't know | **2.3** |
| (none) | **null** |

| Project dimension scores | Expected verdict / weakest |
|---|---|
| 2.0, 2.0, 1.0, others null | fix, weakest = Data (dim 3) |
| 3.0, 3.0, others null | go, weakest = both, partial |
| 4.0, 4.0, others null | ready (partial) |
| all null | not_assessed |

## 4. Data model

Use PostgreSQL (or the team's standard DB).

```
users(id, name, email, role: owner|reviewer|approver|admin, created_at)

dimensions(id 1..8, title, group_name, lead_question, sort_order)

questions(id "5.1", dimension_id, number 1..5, text, is_draft bool, active bool, version int)

projects(
  id uuid, name, business_unit, sponsor, owner_user_id,
  stage: Idea|Feasibility|Build|Pilot / UAT|Production|On hold,
  mode: plan|assess,            -- planning a new project vs assessing an existing one
  due_date date,                -- default 2026-10-30 for existing projects
  created_at, updated_at, archived bool)

answers(
  project_id, question_id,      -- unique pair
  answer: Yes|Partly|No|Dont_know|null,
  evidence text (max 600 chars),
  source: person|ai_interview|ai_evidence,
  confirmed_by user_id null,    -- a person who accepted an AI suggestion
  updated_by user_id, updated_at)

answer_history(id, project_id, question_id, old_answer, new_answer, old_evidence, new_evidence, source, changed_by, changed_at)   -- full audit trail

ai_suggestions(id, project_id, question_id, answer, evidence, source_excerpt, status: pending|accepted|dismissed, created_by, created_at)

briefs(
  id, project_id, created_at, created_by,
  verdict, lowest, weakest jsonb, dimension_scores jsonb, answered int,   -- snapshot of the RULES result at write time
  headline, summary, actions jsonb [{question_id, action, owner}], risks jsonb [string],
  approved bool, approved_by, approved_at)

evidence_files(id, project_id, filename, text_extract, uploaded_by, uploaded_at)
```

Scores are **computed**, not stored (except the snapshot inside a brief).

## 5. Screens

Design reference: `prototype.html`. Dark navy header, teal accent, IBM Plex Sans + IBM Plex Mono for numbers. Light and dark themes. Must work on phone width (~400px). Plain, simple international English in all copy.

### 5.1 Portfolio (home)
- Title "AI project portfolio", eyebrow "Q1 FY27 · assessment due 30 Oct 2026".
- KPI tiles: Projects · Fix before next stage · Go with actions · Ready · Questions answered % with days left to the due date.
- Table, one row per project, sorted fix → go → ready → not assessed:
  project name (link) + BU · stage · mode; 8 coloured score cells (tooltip "x of 5 answered"); weakest link; verdict pill; answered x/40 with a progress bar; owner.
- Filters: business unit, stage, mode, verdict, owner, "my projects".
- Side panel "Where projects get stuck": count of projects per weakest dimension, as bars.
- Buttons: **+ New project**, **AI portfolio summary**, **Export** (CSV and XLSX).
- Rules footnote: "Yes = 5 · Partly = 3 · No = 1 · Don't know = 1. A dimension with any 'No' is capped at 3…"

### 5.2 New project (form)
Fields: name (required), business unit, sponsor, project owner (user picker), stage, mode (Planning a new project / Assessing an existing project), due date. On create, open the Assess screen.

### 5.3 Assess (one project)
- Header: name, BU, sponsor, owner, stage (editable select), mode pill, answered x/40 bar, button "Decision brief →".
- Left rail: 8 dimensions with "x of 5 · has a No" and score chip. Click to switch.
- Centre: dimension card (eyebrow "Dimension n · group", title, lead question, score, "capped at 3 because of a No (raw x)", draft note if draft). Then 5 question cards: ID, text, "AI-suggested" tag when source is AI and not yet confirmed, four answer buttons (click the selected one again to clear), evidence textarea (save on blur), last changed by / when.
- Right: **Agent panel** with two tabs (see section 6).
- Every change writes `answer_history`.

### 5.4 Decision brief
- Verdict (from rules) in large coloured text, "Partial: x of 40 answered" pill, weakest link with score.
- AI headline + summary.
- Scores by dimension: 8 horizontal bars, weakest in bold.
- Top 3 actions as cards: question ID · dimension, action, owner.
- Risks list (max 3).
- Note if questions are open: "x questions are still open. The verdict can change as they are answered."
- Footer: "The AI writes the summary and actions from the answers. The verdict and scores come from fixed rules, so every project is judged the same way."
- Buttons: Write brief with AI / Rewrite brief, **Approve decision** (approver role only), Export PDF, Send to steering committee (email or Teams — phase 2).
- Keep brief history; show the latest by default.

## 6. The agent (AI features)

### 6.1 Principles
- **AI suggests, people decide.** AI never sets the verdict or the score. AI-written answers are marked `source = ai_*` until a person confirms or edits them.
- Every AI call uses only data from this project (no other projects' data, except the portfolio summary).
- Use the CityGPT model routing (OpenRouter) through a backend endpoint. Never call the LLM from the browser. Never send secrets.
- Log every AI call: user, project, feature, model, tokens, cost, latency.
- Ask for JSON; validate it with a schema; reject and show a friendly error if invalid. No automatic retry loops.
- All outputs in plain international English.

### 6.2 Interview mode (fast model)
The agent shows the next unanswered question (current dimension first, then all). The owner answers in their own words. The backend classifies it.

Prompt:
```
You help assess an AI project at City Holdings with a readiness checklist.
Project: {name}. Business unit: {bu}. Sponsor: {sponsor}. Owner: {owner}. Stage: {stage}. Purpose of this check: {planning a new project | assessing an existing project}.
Dimension {n}: {title}. {lead}
Question {id}: {text}
{if earlier vague reply: Earlier answer from the owner on this question: """{context}"""}
The owner now replied: """{reply}"""

Decide the answer. Yes = fully true today. Partly = partly true or in progress. No = not true. Don't know = the reply does not say. Do not guess beyond the reply.
Write "evidence" as one short sentence in plain international English, using only facts from the owner's words.
If the reply is too vague to decide, set "followUp" to one short, simple question that gets the missing fact, and set "answer" to "". Otherwise "followUp" is "".
Reply only with JSON: {"answer":"Yes|Partly|No|Don't know|","evidence":"...","followUp":"..."}
```
UI: chat log; after a recorded answer show "Recorded 5.1: No. <evidence>" with **Undo**. Buttons: Send (Ctrl/Cmd+Enter), Skip, Stop.

### 6.3 Read evidence mode (default model)
The owner pastes text or uploads a file (txt, md, csv, docx, pdf — extract text on the server, max ~24,000 characters sent). The agent returns suggestions; the owner accepts or dismisses each, or accepts all.

Prompt:
```
You help assess an AI project at City Holdings with a 40-question readiness checklist.
{project context line}

Checklist:
{id} {text} [already answered: {answer}]   -- one line per question

Project text from the owner:
"""{text}"""

Find questions that the text clearly answers. Skip questions the text does not cover. Skip questions already answered unless the text clearly changes the answer. Yes = fully true today. Partly = partly true or in progress. No = clearly not true.
For each, write "evidence" as one short plain-English sentence based only on the text.
Reply only with a JSON array, at most 15 items: [{"id":"3.2","answer":"Yes|Partly|No","evidence":"..."}]
```
Drop items with unknown IDs or invalid answers. Store as `ai_suggestions` (pending).

### 6.4 Decision brief (default or strong model)
Compute the rules result first, then send it to the model.

Prompt:
```
Write a short decision brief for a steering committee about an AI project at City Holdings.
{project context line}
The scoring rules already decided: verdict "{verdict}", weakest dimension(s): {weakest} with score {lowest} of 5. Answered {n} of 40 questions.
Dimension scores: {1. Strategy & Priorities 3.0; ...}.
Answers:
{id} {text} → {answer} ({evidence})   -- one line per answered question
Open questions: {ids}.

Do not change the verdict. Use plain international English: short sentences, everyday words.
Reply only with JSON: {"headline":"one sentence","summary":"3 or 4 short sentences on what is in place and what holds the project back","actions":[{"question":"5.1","action":"short action","owner":"a role or name from the answers, else 'To assign'"}],"risks":["short risk"]}. At most 3 actions, aimed at the weakest answers first. At most 3 risks.
```

### 6.5 Portfolio summary (default model, streamed)
```
Summarise this AI project portfolio for City Holdings' steering committee in 4 or 5 short lines of plain international English. Name the main blockers, the projects that need a decision, and how complete the assessment is (deadline 30 Oct 2026). No headings.

{name} ({bu}, {stage}): {verdict}, weakest {dimension} {score}, {n}/40 answered.   -- one line per project
```

## 7. API (suggested)

```
GET    /api/questions
GET    /api/projects?bu=&stage=&mode=&verdict=&owner=
POST   /api/projects
GET    /api/projects/:id                 -> project + answers + computed score
PATCH  /api/projects/:id                 -> stage, owner, etc.
PUT    /api/projects/:id/answers/:qid    -> {answer, evidence, source}
GET    /api/projects/:id/history
POST   /api/projects/:id/agent/interview -> {question_id, reply, context?} => {answer, evidence, followUp}
POST   /api/projects/:id/agent/evidence  -> {text | file} => suggestions[]
POST   /api/suggestions/:id/accept | /dismiss
POST   /api/projects/:id/briefs          -> generate brief (rules + AI)
POST   /api/briefs/:id/approve           -> approver only
POST   /api/portfolio/summary
GET    /api/export.csv  |  /api/export.xlsx
```
Return computed scores from the server using the same `scoreProject` function the UI uses (share one module, or test both against section 3.4).

## 8. Export

- **CSV / XLSX, one row per project × question:** Project, Business unit, Stage, Mode, Dimension, Question ID, Question, Answer, Evidence, Source, Dimension score, Verdict.
- **XLSX extra sheet "Portfolio":** one row per project with the 8 scores, lowest, weakest link, verdict, answered/40.
- Decision brief as PDF (phase 2).

## 9. Seed data (existing projects)

Load these 12 projects (mode `assess`, due 30 Oct 2026). Answers come from the Sep 2026 portfolio tracker and the strategy canvas session; mark them `source = person`.

| Project | BU | Sponsor | Stage | Seed answers |
|---|---|---|---|---|
| Employee Assistant | Hypertrade | Thar Htet | Feasibility | 2.1 Yes "Business owner is the Chief People Officer." · 2.2 No "Tech and AI team know, but the BU / function does not know yet." · 2.3 Yes "Steering Committee has authority to clear bottlenecks." · 2.4 Yes "CHL IT and DAAI IT have committed." · 2.5 Yes "Funding plan beyond the pilot is in place." · 5.1 No "Business owner has not set the quality %." · 5.2 Yes · 5.3 Yes |
| CFC Model | Food & Beverage | | Build | 1.1 Partly "Expected output not yet agreed; a stakeholder meeting is needed before optimising." · 3.2 No "Waiting for the data CFC agreed to send. No movement since the 10 Aug meeting." |
| Fresh Replenishment | Retail / CMHL | | Build | 3.3 No "49% of vegetable SKUs have no expiry or shelf-life data." · 2.4 Partly "Waiting for a timeslot from the CMHL IT head to review the model output." |
| Future Fields Forecasting | Future Fields (SG) | | Build | 3.3 Partly "Only stock-out and return data is available (sales = stock-out minus return)." · 5.2 Partly "Tested: sales prediction error rose from 2.8% to above 14% from August." |
| Ferry Optimisation (pilot) | Hub / Group | Ma Swe | Pilot / UAT | 2.1 Yes "Ma Swe leads the project." · 3.2 Yes "Optimisation model built on CHL hub data." · 7.3 Partly "Ma Swe will arrange a session with the ferry team to share results and agree the pilot." |
| Consumer Insights (City Agent Insights) | Distribution | | Pilot / UAT | 5.2 Yes "UAT and testing completed by the PG team." · 7.3 Yes "PG team ran the UAT." |
| City Agent Insights + Databot | Hub / Group | | Pilot / UAT | 5.2 Partly "Finance is testing it on their own financial data." · 7.3 Partly "Finance team is testing it now." |
| ITSM Agent (ARIA) | All sectors | | Production | 7.5 Partly "Live and announced to sectors; adoption is now the focus." |
| CityGPT Next (City Squad) | Hub / Group | | Build | 4.2 Partly "Platform credentials not issued in mid-Sep; launch moved to 9 Oct." · 7.1 Partly "City Agent Pro training started with Finance; other teams by availability." |
| RO & ED Digital Conversion | Distribution | | Production | none |
| Coverage Planning (MCP) Tool | Distribution | | Production | none |
| City Care Agent | Retail / CMHL | | Production | none |

Default project owner: Rahul Gupta (rahulgupta@cityholdings.com.mm) until each owner is assigned.

## 10. Non-functional requirements

- **Login:** company single sign-on. Only City Holdings staff.
- **Hosting:** inside the CityGPT / City AI estate (AWS ap-southeast-1), same network rules as CityGPT.
- **Audit:** full answer history and AI call log. Nothing is deleted; projects are archived.
- **Privacy:** evidence text and files stay in our database. Only the minimum text goes to the LLM.
- **Accessibility:** real buttons and labels, keyboard use, visible focus, 44px touch targets, contrast 4.5:1.
- **Performance:** portfolio loads in < 2 s for 200 projects.
- **Copy:** plain international English, short sentences. No jargon in user-facing text.

## 11. Later (phase 2+)

- Quarterly reassessment: copy last quarter's answers into a new assessment round and show change since last quarter.
- Reminders to owners with open questions (email / Teams), weekly completion report to the City AI lead.
- Gate check: block a stage change (e.g. Feasibility → Build) while the verdict is "Fix before next stage", unless an approver overrides with a reason.
- Read evidence from SharePoint / Drive / the portfolio tracker automatically.
- Expose the agent inside CityGPT as a tool ("assess my project").
- Brief as PDF in the official City Holdings PowerPoint/Word template.

## 12. Build plan (to meet 30 Oct)

1. **Week of 6 Oct:** DB schema + seed, question admin, `scoreProject` with tests, Portfolio and Assess screens (manual answers), SSO.
2. **Week of 13 Oct:** Agent interview + read evidence, suggestions accept/dismiss, history, export. Owners start filling in.
3. **Week of 20 Oct:** Decision brief + approve, portfolio summary, filters, polish, phone layout.
4. **Week of 27 Oct:** Fixes from owners' use, final review, steering committee pack.

## 13. Definition of done (MVP)

- [x] All 40 questions load from the DB; dimensions 1–2 show "Draft wording".
- [x] Scoring passes every test in 3.4, on server and client.
- [x] An owner can create a project, answer by hand, by interview, and from pasted evidence.
- [x] AI answers are tagged until confirmed; every change is in history with Undo for the last agent answer.
- [x] Decision brief shows the rules verdict, AI summary, 3 actions, risks; approvers can approve.
- [x] Portfolio shows all 12 seed projects with correct scores and verdicts.
- [x] CSV and XLSX export work.
- [x] Works on phone width and in dark mode.
