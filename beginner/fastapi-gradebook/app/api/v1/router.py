from fastapi import APIRouter

from app.api.v1.endpoints import courses, grades, health, students

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(students.router, prefix="/students", tags=["students"])
api_router.include_router(courses.router, prefix="/courses", tags=["courses"])
api_router.include_router(grades.router, prefix="/grades", tags=["grades"])
