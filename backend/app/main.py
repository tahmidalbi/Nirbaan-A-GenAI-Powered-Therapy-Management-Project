from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.router import router as auth_router
from app.patients.router import router as patients_router
from app.emergency_personnel.router import router as emergency_personnel_router
from app.resources.router import router as resources_router
from app.intakes.router import router as intakes_router
from app.self_monitoring.router import router as self_monitoring_router
from app.fear_ladder.router import router as fear_ladder_router
from app.education.fear_ladder.router import router as education_fear_ladder_router
from app.education.ocd_core.router import router as education_ocd_core_router
from app.erp.router import router as erp_router

# Optional: if you have SQLAlchemy Base + engine and want to ensure tables exist in dev
# from app.database.base import Base
# from app.database.session import engine


def create_app() -> FastAPI:
    app = FastAPI(
        title="Nirbaan - Therapy Management Backend",
        version="0.1.0",
        description="Multi-tenant therapy management platform with JWT authentication and RAG",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://localhost:5174",
            "http://localhost:5175",
            "http://localhost:5176",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:5174",
            "http://127.0.0.1:5175",
            "http://127.0.0.1:5176",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    # Routers
    app.include_router(auth_router)
    app.include_router(patients_router)
    app.include_router(emergency_personnel_router)
    app.include_router(resources_router)
    app.include_router(intakes_router)
    app.include_router(self_monitoring_router)
    app.include_router(fear_ladder_router)
    app.include_router(education_fear_ladder_router)
    app.include_router(education_ocd_core_router)
    app.include_router(erp_router)

    @app.get("/", tags=["health"])
    def health_check():
        return {
            "status": "Backend running",
            "message": "Nirbaan Therapy Management API with RAG + Intake AI Summary",
            "version": "0.1.0",
        }

    # Optional startup hook (useful if you want to auto-create tables in dev)
    # @app.on_event("startup")
    # def on_startup():
    #     Base.metadata.create_all(bind=engine)

    return app


app = create_app()
