from fastapi import APIRouter

from app.api.v1.endpoints import auth, health, tasks, teams, users

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(teams.router, prefix="/teams", tags=["teams"])
api_router.include_router(tasks.router, prefix="/teams/{team_id}/tasks", tags=["tasks"])
