from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    field: str | None = None
    reason: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail] = Field(default_factory=list)


class SuccessResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T
    message: str | None = None
    request_id: str | None = Field(default=None, alias="requestId")

    model_config = {"populate_by_name": True}


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorBody
    request_id: str | None = Field(default=None, alias="requestId")

    model_config = {"populate_by_name": True}
