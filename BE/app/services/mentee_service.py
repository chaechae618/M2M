from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import DomainError
from app.models.auth import User
from app.models.mentee import MenteeExperience, MenteeProfile
from app.schemas.mentee import ExperienceCreateRequest, ExperienceUpdateRequest


class MenteeService:
    def __init__(self, db: Session, user: User) -> None:
        self.db = db
        self.user = user

    def get_profile(self) -> MenteeProfile:
        profile = self.db.scalar(
            select(MenteeProfile).where(MenteeProfile.user_id == self.user.id)
        )
        if profile is None:
            raise DomainError("MENTEE_PROFILE_NOT_FOUND", "멘티 프로필을 찾을 수 없습니다.", 404)
        return profile

    def list_experiences(self) -> list[MenteeExperience]:
        return list(
            self.db.scalars(
                select(MenteeExperience)
                .where(MenteeExperience.mentee_id == self.user.id)
                .order_by(MenteeExperience.created_at.desc())
            )
        )

    def create_experience(self, payload: ExperienceCreateRequest) -> MenteeExperience:
        experience = MenteeExperience(
            mentee_id=self.user.id,
            **payload.model_dump(),
        )
        self.db.add(experience)
        self.db.commit()
        self.db.refresh(experience)
        return experience

    def get_experience(self, experience_id: str) -> MenteeExperience:
        experience = self.db.scalar(
            select(MenteeExperience).where(
                MenteeExperience.id == experience_id,
                MenteeExperience.mentee_id == self.user.id,
            )
        )
        if experience is None:
            raise DomainError("EXPERIENCE_NOT_FOUND", "경험을 찾을 수 없습니다.", 404)
        return experience

    def update_experience(
        self,
        experience_id: str,
        payload: ExperienceUpdateRequest,
    ) -> MenteeExperience:
        experience = self.get_experience(experience_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(experience, field, value)
        self.db.commit()
        self.db.refresh(experience)
        return experience

    def delete_experience(self, experience_id: str) -> None:
        experience = self.get_experience(experience_id)
        self.db.delete(experience)
        self.db.commit()
