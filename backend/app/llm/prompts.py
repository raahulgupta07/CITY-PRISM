"""Prompts from SPEC section 6, word for word. Only this project's data goes in."""

from __future__ import annotations

from collections.abc import Iterable

from app.db.models import Dimension, Project, Question

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
