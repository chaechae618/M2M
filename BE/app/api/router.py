from fastapi import APIRouter

from app.api.v1 import auth, consultations, feedback, jobs, mentees, personas, qna

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(mentees.router)
api_router.include_router(consultations.router)
api_router.include_router(personas.router)
api_router.include_router(feedback.router)
api_router.include_router(qna.router)
api_router.include_router(jobs.router)
