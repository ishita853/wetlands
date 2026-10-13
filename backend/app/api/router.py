from fastapi import APIRouter

from app.api.routes import admin, auth, climate, datasets, water_quality, wetlands

api_router = APIRouter()
api_router.include_router(wetlands.router)
api_router.include_router(climate.router)
api_router.include_router(water_quality.router)
api_router.include_router(datasets.router)
api_router.include_router(auth.router)
api_router.include_router(admin.router)
