from datetime import datetime

from pydantic import BaseModel, Field


class MenteeProfileUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=50)
    current_status: str | None = Field(default=None, alias="currentStatus", max_length=30)
    background: dict | None = None
    considering_options: list[str] | None = Field(default=None, alias="consideringOptions")
    target_roles: list[str] | None = Field(default=None, alias="targetRoles")
    interest_domains: list[str] | None = Field(default=None, alias="interestDomains")

    model_config = {"populate_by_name": True}


class MenteeProfileResponse(BaseModel):
    id: str
    email: str
    name: str
    current_status: str = Field(alias="currentStatus")
    background: dict
    considering_options: list[str] = Field(alias="consideringOptions")
    target_roles: list[str] = Field(alias="targetRoles")
    interest_domains: list[str] = Field(alias="interestDomains")
    resume_url: str | None = Field(alias="resumeUrl")
    portfolio_url: str | None = Field(alias="portfolioUrl")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = {"populate_by_name": True, "from_attributes": True}


class ExperienceCreateRequest(BaseModel):
    experience_type: str = Field(alias="experienceType", min_length=1, max_length=30)
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=5000)
    organization: str | None = Field(default=None, max_length=200)
    start_date: str | None = Field(default=None, alias="startDate", pattern=r"^\d{4}-\d{2}$")
    end_date: str | None = Field(default=None, alias="endDate", pattern=r"^\d{4}-\d{2}$")
    role: str | None = Field(default=None, max_length=200)
    key_skills: list[str] = Field(default_factory=list, alias="keySkills")
    tools: list[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class ExperienceUpdateRequest(BaseModel):
    experience_type: str | None = Field(
        default=None, alias="experienceType", min_length=1, max_length=30
    )
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, min_length=1, max_length=5000)
    organization: str | None = Field(default=None, max_length=200)
    start_date: str | None = Field(default=None, alias="startDate", pattern=r"^\d{4}-\d{2}$")
    end_date: str | None = Field(default=None, alias="endDate", pattern=r"^\d{4}-\d{2}$")
    role: str | None = Field(default=None, max_length=200)
    key_skills: list[str] | None = Field(default=None, alias="keySkills")
    tools: list[str] | None = None

    model_config = {"populate_by_name": True}


class ExperienceResponse(BaseModel):
    id: str
    experience_type: str = Field(alias="experienceType")
    title: str
    description: str
    organization: str | None
    start_date: str | None = Field(alias="startDate")
    end_date: str | None = Field(alias="endDate")
    role: str | None
    key_skills: list[str] = Field(alias="keySkills")
    tools: list[str]
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = {"populate_by_name": True, "from_attributes": True}


class FileUploadResponse(BaseModel):
    file_type: str = Field(alias="fileType")
    file_name: str = Field(alias="fileName")
    url: str
    size: int

    model_config = {"populate_by_name": True}
