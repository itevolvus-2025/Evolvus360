"""Version one API router with the shared response contract."""

from fastapi import APIRouter

from app.core.routing import ResponseContractRoute

api_router = APIRouter(route_class=ResponseContractRoute)
