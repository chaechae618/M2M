from pydantic import BaseModel, Field


class QnaPostCreateRequest(BaseModel):
    category: str = Field(min_length=1, max_length=50)
    title: str = Field(min_length=2, max_length=120)
    content: str = Field(min_length=5, max_length=10000)
    image_ids: list[str] = Field(default_factory=list, alias="imageIds", max_length=5)
    anonymous: bool = False

    model_config = {"populate_by_name": True}


class QnaPostUpdateRequest(BaseModel):
    category: str | None = Field(default=None, min_length=1, max_length=50)
    title: str | None = Field(default=None, min_length=2, max_length=120)
    content: str | None = Field(default=None, min_length=5, max_length=10000)
    image_ids: list[str] | None = Field(default=None, alias="imageIds", max_length=5)
    anonymous: bool | None = None

    model_config = {"populate_by_name": True}


class QnaCommentCreateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=3000)
    anonymous: bool = False


class QnaCommentUpdateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=3000)
    anonymous: bool | None = None
