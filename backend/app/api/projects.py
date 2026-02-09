from fastapi import APIRouter

from app.core.deps import AccessibleProject
from app.schemas import ProjectOut

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("/{project_id}", response_model=ProjectOut)
def read(project: AccessibleProject) -> ProjectOut:
    return ProjectOut.model_validate(project)
