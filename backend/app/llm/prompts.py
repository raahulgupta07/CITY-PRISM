"""Prompts from SPEC section 6, word for word. Only this project's data goes in."""

from __future__ import annotations

from collections.abc import Iterable

from app.db.models import Dimension, Project, Question
from app.scoring import TOTAL_QUESTIONS, VERDICT_LABELS, ScoreResult

PURPOSE = {"plan": "planning a new project", "assess": "assessing an existing project"}
ANSWER_TEXT = {"Yes": "Yes", "Partly": "Partly", "No": "No", "Dont_know": "Don't know"}


def context_line(project: Project, owner_name: str) -> str:
    return (
        f"Project: {project.name}. Business unit: {project.business_unit}. "
        f"Sponsor: {project.sponsor}. Owner: {owner_name}. Stage: {project.stage}. "
        f"Purpose of this check: {PURPOSE[project.mode]}."
    )


def interview_prompt(
    project: Project,
    owner_name: str,
    dimension: Dimension,
    question: Question,
    reply: str,
    context: str = "",
) -> str:
    """SPEC 6.2 (fast model)."""
    lines = [
        "You help assess an AI project at City Holdings with a readiness checklist.",
        context_line(project, owner_name),
        f"Dimension {dimension.id}: {dimension.title}. {dimension.lead_question}",
        f"Question {question.id}: {question.text}",
    ]
    if context:
        lines.append(f'Earlier answer from the owner on this question: """{context}"""')
    lines += [
        f'The owner now replied: """{reply}"""',
        "",
        "Decide the answer. Yes = fully true today. Partly = partly true or in progress. "
        "No = not true. Don't know = the reply does not say. Do not guess beyond the reply.",
        'Write "evidence" as one short sentence in plain international English, using only '
        "facts from the owner's words.",
        'If the reply is too vague to decide, set "followUp" to one short, simple question '
        'that gets the missing fact, and set "answer" to "". Otherwise "followUp" is "".',
        'Reply only with JSON: {"answer":"Yes|Partly|No|Don\'t know|","evidence":"...",'
        '"followUp":"..."}',
    ]
    return "\n".join(lines)


def evidence_prompt(
    project: Project,
    owner_name: str,
    questions: Iterable[Question],
    answered: dict[str, str | None],
    text: str,
) -> str:
    """SPEC 6.3 (default model)."""
    checklist = []
    for q in questions:
        line = f"{q.id} {q.text}"
        current = answered.get(q.id)
        if current:
            line += f" [already answered: {ANSWER_TEXT[current]}]"
        checklist.append(line)
    return "\n".join(
        [
            "You help assess an AI project at City Holdings with a 40-question readiness "
            "checklist.",
            context_line(project, owner_name),
            "",
            "Checklist:",
            *checklist,
            "",
            "Project text from the owner:",
            f'"""{text}"""',
            "",
            "Find questions that the text clearly answers. Skip questions the text does not "
            "cover. Skip questions already answered unless the text clearly changes the answer. "
            "Yes = fully true today. Partly = partly true or in progress. No = clearly not true.",
            'For each, write "evidence" as one short plain-English sentence based only on the '
            "text.",
            "Reply only with a JSON array, at most 15 items: "
            '[{"id":"3.2","answer":"Yes|Partly|No","evidence":"..."}]',
        ]
    )


def _score(value: float | None) -> str:
    return "not answered" if value is None else f"{value:.1f}"


def brief_prompt(
    project: Project,
    owner_name: str,
    dimensions: list[Dimension],
    questions: list[Question],
    answers: dict[str, tuple[str | None, str]],
    result: ScoreResult,
) -> str:
    """SPEC 6.4. The rules result is computed first and sent as fixed facts."""
    titles = {d.id: d.title for d in dimensions}
    weakest = " and ".join(titles[d] for d in result.weakest) or "none"
    scores = "; ".join(
        f"{d.id}. {titles[d.id]} {_score(d.score)}" for d in result.dimensions if d.id in titles
    )
    lines, open_ids = [], []
    for q in questions:
        answer, evidence = answers.get(q.id, (None, ""))
        if not answer:
            open_ids.append(q.id)
            continue
        line = f"{q.id} {q.text} → {ANSWER_TEXT[answer]}"
        if evidence:
            line += f" ({evidence})"
        lines.append(line)
    return "\n".join(
        [
            "Write a short decision brief for a steering committee about an AI project at "
            "City Holdings.",
            context_line(project, owner_name),
            f'The scoring rules already decided: verdict "{VERDICT_LABELS[result.verdict]}", '
            f"weakest dimension(s): {weakest} with score {_score(result.lowest)} of 5. "
            f"Answered {result.answered} of {TOTAL_QUESTIONS} questions.",
            f"Dimension scores: {scores}.",
            "Answers:",
            *lines,
            f"Open questions: {', '.join(open_ids) or 'none'}.",
            "",
            "Do not change the verdict. Use plain international English: short sentences, "
            "everyday words.",
            'Reply only with JSON: {"headline":"one sentence","summary":"3 or 4 short sentences '
            'on what is in place and what holds the project back","actions":[{"question":"5.1",'
            '"action":"short action","owner":"a role or name from the answers, else \'To assign\'"'
            '}],"risks":["short risk"]}. At most 3 actions, aimed at the weakest answers first. '
            "At most 3 risks.",
        ]
    )


def summary_prompt(rows: Iterable[tuple[Project, ScoreResult]], titles: dict[int, str]) -> str:
    """SPEC 6.5. The only prompt that holds more than one project."""
    lines = []
    for project, result in rows:
        verdict = VERDICT_LABELS[result.verdict]
        if result.weakest:
            weakest = " and ".join(titles[d] for d in result.weakest)
            middle = f"weakest {weakest} {_score(result.lowest)}, "
        else:
            middle = ""
        bu = project.business_unit or "no business unit"
        lines.append(
            f"{project.name} ({bu}, {project.stage}): {verdict}, {middle}"
            f"{result.answered}/{TOTAL_QUESTIONS} answered."
        )
    return "\n".join(
        [
            "Summarise this AI project portfolio for City Holdings' steering committee in 4 or 5 "
            "short lines of plain international English. Name the main blockers, the projects "
            "that need a decision, and how complete the assessment is (deadline 30 Oct 2026). "
            "No headings.",
            "",
            *lines,
        ]
    )
