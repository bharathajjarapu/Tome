from fastapi import APIRouter, HTTPException, status

from tome.core.db import Db
from tome.core.deps import AccessibleProject, CurrentUser
from tome.schemas import ProjectIn, ProjectOut
from tome.services import projects

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create(body: ProjectIn, user: CurrentUser, db: Db) -> ProjectOut:
    project = projects.create(db, user.id, body.name)
    if project is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No team to create a project in")
    return ProjectOut.model_validate(project)


@router.get("", response_model=list[ProjectOut])
def index(user: CurrentUser, db: Db) -> list[ProjectOut]:
    return [ProjectOut.model_validate(p) for p in projects.listfor(db, user.id)]


@router.get("/{project_id}", response_model=ProjectOut)
def read(project: AccessibleProject) -> ProjectOut:
    return ProjectOut.model_validate(project)
