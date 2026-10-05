from __future__ import annotations

import pytest

from app.db.models import Project, User
from app.services import permissions as perm

OWNER = User(id="u-owner", name="O", email="o@x", role="owner")
OTHER_OWNER = User(id="u-other", name="P", email="p@x", role="owner")
REVIEWER = User(id="u-rev", name="R", email="r@x", role="reviewer")
APPROVER = User(id="u-app", name="A", email="a@x", role="approver")
ADMIN = User(id="u-adm", name="D", email="d@x", role="admin")
PROJECT = Project(id="p1", name="P", owner_user_id=OWNER.id)


@pytest.mark.parametrize(
    ("user", "expected"),
    [(OWNER, True), (OTHER_OWNER, False), (REVIEWER, True), (APPROVER, False), (ADMIN, True)],
)
def test_edit_project(user: User, expected: bool) -> None:
    assert perm.can_edit_project(user, PROJECT) is expected


@pytest.mark.parametrize(
    ("user", "create", "archive", "approve", "manage"),
    [
        (OWNER, True, False, False, False),
        (REVIEWER, True, True, False, False),
        (APPROVER, False, False, True, False),
        (ADMIN, True, True, False, True),
    ],
)
def test_role_matrix(user: User, create: bool, archive: bool, approve: bool, manage: bool) -> None:
    assert perm.can_create_project(user) is create
    assert perm.can_archive_project(user) is archive
    assert perm.can_approve_brief(user) is approve
    assert perm.can_manage(user) is manage


def test_unowned_project_only_for_reviewer_and_admin() -> None:
    orphan = Project(id="p2", name="Q", owner_user_id=None)
    assert not perm.can_edit_project(OWNER, orphan)
    assert perm.can_edit_project(REVIEWER, orphan)
