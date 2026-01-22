import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Citation,
    Conversation,
    Document,
    IngestionJob,
    Membership,
    Message,
    Project,
    Role,
    State,
    Team,
    User,
)


def seed(db: Session) -> tuple[Document, Citation]:
    user = User(email="a@example.com", password_hash="x")
    team = Team(name="Team A")
    db.add_all([user, team])
    db.flush()
    db.add(Membership(user_id=user.id, team_id=team.id))
    project = Project(team_id=team.id, name="Docs")
    db.add(project)
    db.flush()
    doc = Document(project_id=project.id, filename="a.pdf", storage_key="k", sha256="s")
    conversation = Conversation(project_id=project.id, user_id=user.id)
    db.add_all([doc, conversation])
    db.flush()
    db.add(IngestionJob(document_id=doc.id))
    message = Message(conversation_id=conversation.id, role=Role.user, content="hi")
    db.add(message)
    db.flush()
    citation = Citation(
        message_id=message.id, document_id=doc.id, chunk_id="c1", page=2, snippet="text"
    )
    db.add(citation)
    db.commit()
    return doc, citation


def test_round_trip(db: Session) -> None:
    doc, _ = seed(db)
    stored = db.get(Document, doc.id)
    assert stored is not None
    assert stored.state is State.uploaded
    assert stored.error is None
    assert isinstance(stored.id, uuid.UUID)

    job = db.scalars(select(IngestionJob).where(IngestionJob.document_id == doc.id)).one()
    assert job.attempts == 0


def test_deleting_document_removes_its_citations(db: Session) -> None:
    doc, citation = seed(db)
    db.delete(doc)
    db.commit()
    db.expunge_all()
    assert db.scalars(select(Citation).where(Citation.id == citation.id)).first() is None
