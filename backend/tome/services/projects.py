import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from tome.models import Membership, Project


def teamids(db: Session, userid: uuid.UUID) -> Sequence[uuid.UUID]:
    return db.scalars(select(Membership.team_id).where(Membership.user_id == userid)).all()


def create(db: Session, userid: uuid.UUID, name: str) -> Project | None:
    """Create a project in the caller's team, or None if they belong to no team."""
    # ponytail: a user has one personal team today; add a team_id argument when teams can be joined.
    teams = teamids(db, userid)
    if not teams:
        return None
    project = Project(team_id=teams[0], name=name)
    db.add(project)
    db.commit()
    return project


def listfor(db: Session, userid: uuid.UUID) -> Sequence[Project]:
    teams = teamids(db, userid)
    return db.scalars(
        select(Project).where(Project.team_id.in_(teams)).order_by(Project.created_at)
    ).all()
