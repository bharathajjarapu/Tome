import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from pka.core.security import hash_password, verify_password
from pka.models import Membership, Team, User


def find_user(db: Session, email: str) -> User | None:
    return db.scalars(select(User).where(User.email == email)).first()


def register(db: Session, email: str, password: str) -> User:
    """Create the user plus the personal team they own. Caller checks for duplicates."""
    user = User(email=email, password_hash=hash_password(password))
    team = Team(name=email.split("@")[0])
    db.add_all([user, team])
    db.flush()
    db.add(Membership(user_id=user.id, team_id=team.id))
    db.commit()
    return user


def authenticate(db: Session, email: str, password: str) -> uuid.UUID | None:
    user = find_user(db, email)
    if user is None or not verify_password(password, user.password_hash):
        return None
    return user.id
