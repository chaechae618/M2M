import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

import app.models  # noqa: F401
from app.api.router import api_router
from app.api.v1.health import router as health_router
from app.core.config import get_settings
from app.core.exceptions import DomainError
from app.db.base import Base
from app.db.session import engine
from app.db.sqlite_compat import ensure_sqlite_compatibility

settings = get_settings()
upload_root = settings.upload_root


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # Windows 콘솔 기본 코드페이지(cp949)는 ✓/✗ 같은 유니코드 기호를 인코딩하지 못해
    # 에이전트 로그의 print()가 UnicodeEncodeError로 죽는 걸 막는다.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    upload_root.mkdir(parents=True, exist_ok=True)
    if settings.auto_create_tables and settings.is_development:
        ensure_sqlite_compatibility(engine)
        Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Request-Id"],
)
app.mount("/uploads", StaticFiles(directory=upload_root, check_dir=False), name="uploads")


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-Id") or f"req_{uuid4()}"
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-Id"] = request_id
    return response


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            },
            "requestId": request.state.request_id,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = []
    for error in exc.errors():
        location = error.get("loc", [])
        field = ".".join(str(part) for part in location if part != "body")
        details.append({"field": field or None, "reason": error.get("msg", "검증 실패")})
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "입력값을 확인해주세요.",
                "details": details,
            },
            "requestId": request.state.request_id,
        },
    )


app.include_router(health_router)
app.include_router(api_router, prefix=settings.api_v1_prefix)
