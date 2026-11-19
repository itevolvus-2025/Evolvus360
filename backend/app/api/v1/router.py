"""Version one API router with the shared response contract."""

from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.entities import router as entities_router
from app.api.v1.endpoints.master_data import router as master_data_router
from app.api.v1.endpoints.onboarding import router as onboarding_router
from app.api.v1.endpoints.roles import router as roles_router
from app.api.v1.endpoints.users import router as users_router
from app.core.routing import ResponseContractRoute

api_router = APIRouter(route_class=ResponseContractRoute)
api_router.include_router(auth_router)
api_router.include_router(entities_router)
api_router.include_router(master_data_router)
api_router.include_router(users_router)
api_router.include_router(onboarding_router)
api_router.include_router(roles_router)
