"""Who can do what (SPEC section 2). Every write route checks these.

Everyone signed in can read the portfolio and every project.
"""

from __future__ import annotations

from app.db.models import Project, User

EDIT_ANY = ("reviewer", "admin")


def can_create_project(user: User) -> bool:
    return user.role in ("owner", "reviewer", "admin")


def can_edit_project(user: User, project: Project) -> bool:
    """Answer questions, use the agent, write a brief, change stage."""
    if user.role in EDIT_ANY:
        return True
    return user.role == "owner" and project.owner_user_id == user.id


def can_archive_project(user: User) -> bool:
    return user.role in EDIT_ANY


def can_approve_brief(user: User) -> bool:
    return user.role == "approver"


def can_manage(user: User) -> bool:
    """Users and roles, the question set, export of everything."""
    return user.role == "admin"
