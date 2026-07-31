from pydantic import BaseModel, Field


class FeedbackCreateRequest(BaseModel):
    answer_id: str = Field(alias="answerId")
    rating: int = Field(ge=1, le=5)
    helpful_tags: list[str] = Field(default_factory=list, alias="helpfulTags")
    comment: str | None = Field(default=None, max_length=2000)

    model_config = {"populate_by_name": True}


class ReuseConsentRequest(BaseModel):
    answer_id: str = Field(alias="answerId")
    consent: bool
    scope: str = Field(default="anonymized_rag", max_length=50)

    model_config = {"populate_by_name": True}
