from fastapi import APIRouter
from sqlalchemy import text

from app.api.deps import DbSession
from app.schemas.common import SuccessResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=SuccessResponse[dict[str, str]])
def health() -> SuccessResponse[dict[str, str]]:
    return SuccessResponse(data={"status": "ok"})


@router.get("/ready", response_model=SuccessResponse[dict[str, str]])
def ready(db: DbSession) -> SuccessResponse[dict[str, str]]:
    db.execute(text("SELECT 1"))
    return SuccessResponse(data={"status": "ready", "database": "ok"})
