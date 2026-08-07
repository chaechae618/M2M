from fastapi import APIRouter

from app.api.v1 import (
    auth,
    coffee_chats,
    consultations,
    feedback,
    jobs,
    mentees,
    mentor_catalog,
    personas,
    qna,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(coffee_chats.router)
api_router.include_router(mentees.router)
api_router.include_router(consultations.router)
api_router.include_router(personas.router)
api_router.include_router(mentor_catalog.router)
api_router.include_router(feedback.router)
api_router.include_router(qna.router)
api_router.include_router(jobs.router)
