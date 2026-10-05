"""The readiness framework from SPEC section 3.1, used to seed the database.

After seeding, the database is the source of truth: the admin edits questions
there, and the seed never overwrites them.
"""

from __future__ import annotations

# (id, title, group, lead question, draft, [5 questions])
DIMENSIONS: list[tuple[int, str, str, str, bool, list[str]]] = [
    (
        1,
        "Strategy & Priorities",
        "Direction",
        "Is this the right use case, and will its value reach the P&L?",
        True,
        [
            "Is the business problem and the target outcome clearly stated?",
            "Does the use case support a 2030 aspiration or a stated business priority?",
            "Have we estimated the expected value?",
            "Is this use case a priority compared with other use cases?",
            "Is there a clear path for the benefits to reach the P&L?",
        ],
    ),
    (
        2,
        "Ownership & Delivery",
        "Foundations",
        "Does the application have a clear owner and committed resources to move from idea "
        "to sustained operation?",
        True,
        [
            "Is there a named business owner?",
            "Are responsibilities clear to the business unit or function?",
            "Does someone have authority to clear bottlenecks?",
            "Have the business unit and IT committed people to it?",
            "Is there a funding plan beyond the pilot?",
        ],
    ),
    (
        3,
        "Data & Knowledge",
        "Foundations",
        "Does the application have access to the required data and business knowledge, and "
        "can both remain current?",
        False,
        [
            "Have we identified the data, documents and knowledge the application needs?",
            "Can we access these sources, with permission to use them for this use case?",
            "Are the sources accurate, complete, consistent and current enough?",
            "Have we captured the business rules, exceptions and examples that experts use?",
            "Who owns the sources and manages changes to them?",
        ],
    ),
    (
        4,
        "Technology & Engineering",
        "Foundations",
        "Can the team build, integrate, monitor and maintain the application at the required "
        "scale and cost?",
        False,
        [
            "Can it use a shared GenAI platform and existing components?",
            "Can it connect to the enterprise systems it needs to read from or act within?",
            "Can people use it inside the tools and workflow they already rely on?",
            "Can the team monitor usage, errors and cost in production?",
            "Can models or vendors change without rebuilding the application?",
        ],
    ),
    (
        5,
        "Quality & Assurance",
        "Adoption",
        "Can the team show that the application is good enough and safe enough for its "
        "intended use, with the correct fallbacks and human oversight?",
        False,
        [
            "Has the business agreed a quality threshold before launch?",
            "Can the team test quality using representative real cases?",
            "Will the team retest after model, prompt or data changes?",
            "Can users verify outputs and see the supporting sources?",
            "Are oversight, escalation and fallback arrangements clear?",
        ],
    ),
    (
        6,
        "Workflow & Role Redesign",
        "Adoption",
        "Has the work been redesigned around the application, with a clear division between "
        "people and AI?",
        False,
        [
            "Have we mapped the current work, including handoffs, approvals and exceptions?",
            "Which tasks should change rather than simply receive an AI layer?",
            "Which tasks belong to AI, which remain with people, and who decides when AI is "
            "uncertain?",
            "Could faster output create a downstream bottleneck?",
            "Do procedures and decision rights reflect the proposed way of working?",
        ],
    ),
    (
        7,
        "People & Adoption",
        "Adoption",
        "Are the people who will use the application able and willing to work with it?",
        False,
        [
            "Do users have the skills to use the application and judge its output?",
            "Will practical support be available during early adoption?",
            "Have future users helped shape and test the application?",
            "Do leaders visibly support and use it?",
            "Will the team track meaningful adoption and address the reasons people disengage?",
        ],
    ),
    (
        8,
        "Value Capture & Improvement",
        "Scale",
        "Will the application produce measurable results, tracked against its baseline and "
        "total cost?",
        False,
        [
            "Have we agreed the baseline and outcome measures?",
            "How will the organisation use any capacity released by the application?",
            "Will the expected benefit appear in the business owner's targets or budget?",
            "Will benefits be tracked against development and running costs?",
            "What routine will improve the application after launch?",
        ],
    ),
]
