from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, computed_field


class RefinedQuestionRevision(BaseModel):
    used: int = Field(ge=0, le=3)
    limit: Literal[3] = 3

    @computed_field
    @property
    def remaining(self) -> int:
        return max(0, self.limit - self.used)

    @computed_field(alias="canRegenerate")
    @property
    def can_regenerate(self) -> bool:
        return self.used < self.limit

    @computed_field(alias="canEditDirectly")
    @property
    def can_edit_directly(self) -> bool:
        return True


class ConsultationCreateRequest(BaseModel):
    initial_message: str = Field(alias="initialMessage", min_length=1, max_length=3000)

    model_config = {"populate_by_name": True}


class ConsultationMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=5000)


class RefinedQuestionRegenerateRequest(BaseModel):
    instruction: str = Field(min_length=1, max_length=1000)


class RefinedQuestionUpdateRequest(BaseModel):
    content: str = Field(min_length=10, max_length=3000)


class PersonaSelectionRequest(BaseModel):
    persona_id: str = Field(alias="personaId", min_length=1, max_length=80)

    model_config = {"populate_by_name": True}


class ConsultationSummary(BaseModel):
    id: str
    title: str
    status: str
    refined_question: str | None = Field(alias="refinedQuestion")
    refined_question_revision: RefinedQuestionRevision = Field(alias="refinedQuestionRevision")
    route: str | None
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = {"populate_by_name": True}
