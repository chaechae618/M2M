from datetime import datetime

from pydantic import BaseModel, Field


class CoffeeChatCreateRequest(BaseModel):
    persona_id: str = Field(alias="personaId", min_length=1, max_length=80)
    request_message: str = Field(alias="requestMessage", min_length=10, max_length=2000)
    preferred_at: datetime | None = Field(default=None, alias="preferredAt")

    model_config = {"populate_by_name": True}


class CoffeeChatUpdateRequest(BaseModel):
    persona_id: str | None = Field(default=None, alias="personaId", min_length=1, max_length=80)
    request_message: str | None = Field(
        default=None,
        alias="requestMessage",
        min_length=10,
        max_length=2000,
    )
    preferred_at: datetime | None = Field(default=None, alias="preferredAt")

    model_config = {"populate_by_name": True}
