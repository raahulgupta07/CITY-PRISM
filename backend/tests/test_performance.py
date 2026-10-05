"""SPEC 10: the portfolio loads in under 2 seconds with 200 projects."""

from __future__ import annotations

import random
import time

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import Answer, Project, User
from tests.conftest import login


def test_portfolio_with_200_projects(client: TestClient, db: Session) -> None:
    rng = random.Random(7)
    owner = db.query(User).filter_by(email="owner@dev.local").one()
    for i in range(188):  # plus the 12 seed projects = 200
        p = Project(
            name=f"Load test {i:03}",
            business_unit="Load",
            owner_user_id=owner.id,
            stage="Build",
            mode="assess",
        )
        db.add(p)
        db.flush()
        for d in range(1, 9):
            for n in range(1, 6):
                if rng.random() < 0.7:
                    db.add(
                        Answer(
                            project_id=p.id,
                            question_id=f"{d}.{n}",
                            answer=rng.choice(["Yes", "Partly", "No", "Dont_know"]),
                            evidence="Some evidence text " * 5,
                            source="person",
                        )
                    )
    db.commit()
    login(client, "approver@dev.local")
    start = time.perf_counter()
    r = client.get("/api/projects")
    elapsed = time.perf_counter() - start
    assert r.status_code == 200 and len(r.json()) == 200
    assert elapsed < 2.0, f"took {elapsed:.2f} s"
