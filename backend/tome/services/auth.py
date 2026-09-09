import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from tome.core.security import hash_password, verify_password
from tome.models import Membership, Team, User

DUMMY_HASH = hash_password("timing-equaliser")


def find_user(db: Session, email: str) -> User | None:
    return db.scalars(select(User).where(User.email == email)).first()


def register(db: Session, email: str, password: str) -> User | None:
    """Create the user plus the personal team they own. None when the email is taken."""
    user = User(email=email, password_hash=hash_password(password))
    team = Team(name=email.split("@")[0])
    db.add_all([user, team])
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        return None
    db.add(Membership(user_id=user.id, team_id=team.id))
    db.commit()
    return user


def authenticate(db: Session, email: str, password: str) -> uuid.UUID | None:
    user = find_user(db, email)
    # An unknown email still pays for one bcrypt check, so timing does not reveal accounts.
    hashed = user.password_hash if user else DUMMY_HASH
    if not verify_password(password, hashed) or user is None:
        return None
    return user.id
