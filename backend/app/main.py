from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.auth.router import router as auth_router
from app.patients.router import router as patients_router
from app.emergency_personnel.router import router as emergency_personnel_router
from app.resources.router import router as resources_router
from app.intakes.router import router as intakes_router
from app.self_monitoring.router import router as self_monitoring_router
from app.fear_ladder.router import router as fear_ladder_router
from app.education.fear_ladder.router import router as education_fear_ladder_router
from app.education.ocd_core.router import router as education_ocd_core_router
from app.education.erp.router import router as education_erp_router

# sysproj: live video sessions + patient homework
from app.live_sessions.router import router as live_sessions_router
from app.live_sessions.websocket import router as websocket_router
from app.live_sessions.streaming_transcription import router as streaming_transcription_router
from app.patient_homework.router import router as patient_homework_router

# Nirbaan: ERP, AI, therapy session transcripts, chat
from app.erp.router import router as erp_router
from app.progress.router import router as progress_router
from app.NirbaanAIPatient.router import router as nirbaan_ai_patient_router
from app.NirbaanAITherapist.router import router as nirbaan_ai_therapist_router
from app.therapy_sessions.router import router as therapy_sessions_router
from app.chat.router import router as chat_router
from app.chat.ep_router import ep_router
from app.chat.ep_group_router import ep_group_router
from app.chat.ep_patient_router import ep_patient_router
from app.erp.voice.realtime import router as voice_router

# Imaginal Script Generator
from app.ERPScriptGenerator.graph import compile_graph
from app.ERPScriptGenerator.router import router as imaginal_generator_router

# Optional: if you have SQLAlchemy Base + engine and want to ensure tables exist in dev
# from app.database.base import Base
# from app.database.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    App startup/shutdown lifecycle.

    We compile the LangGraph imaginal generator once at startup and keep the
    PostgresSaver context open for the whole app lifetime.
    """
    graph = None
    checkpointer_cm = None

    try:
        graph, checkpointer_cm = compile_graph()
        app.state.imaginal_graph = graph
        app.state.imaginal_checkpointer_cm = checkpointer_cm
        print("Imaginal Script Generator graph initialized.")
        yield
    finally:
        try:
            if checkpointer_cm is not None:
                checkpointer_cm.__exit__(None, None, None)
                print("Imaginal Script Generator checkpointer closed.")
        except Exception as e:
            print(f"Error while closing imaginal graph checkpointer: {e}")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Nirbaan - Therapy Management Backend",
        version="0.1.0",
        description="Multi-tenant therapy management platform with JWT authentication and RAG",
        lifespan=lifespan,
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

    # Shared routers (both branches)
    app.include_router(auth_router)
    app.include_router(patients_router)
    app.include_router(emergency_personnel_router)
    app.include_router(resources_router)
    app.include_router(intakes_router)
    app.include_router(self_monitoring_router)
    app.include_router(fear_ladder_router)
    app.include_router(education_fear_ladder_router)
    app.include_router(education_ocd_core_router)
    app.include_router(education_erp_router)

    # sysproj routers: live video sessions + homework
    app.include_router(live_sessions_router)
    app.include_router(patient_homework_router)
    app.include_router(websocket_router, prefix="/api/therapy-sessions")
    app.include_router(streaming_transcription_router, prefix="/api/therapy-sessions")

    # Nirbaan routers: ERP, AI, therapy records, chat
    app.include_router(erp_router)
    app.include_router(progress_router)
    app.include_router(nirbaan_ai_patient_router)
    app.include_router(nirbaan_ai_therapist_router)
    app.include_router(therapy_sessions_router)
    app.include_router(chat_router)
    app.include_router(ep_router)
    app.include_router(ep_group_router)
    app.include_router(ep_patient_router)
    app.include_router(voice_router)

    # Imaginal Script Generator router
    app.include_router(imaginal_generator_router)

    @app.get("/", tags=["health"])
    def health_check():
        return {
            "status": "Backend running",
            "message": "Nirbaan Therapy Management API with RAG + Intake AI Summary",
            "version": "0.1.0",
            "imaginal_generator_graph": hasattr(app.state, "imaginal_graph"),
        }

    @app.get("/health/celery", tags=["health"])
    def celery_health():
        """
        Checks:
        1. Are any Celery workers alive? (ping)
        2. Are the critical ERP tasks registered on those workers?
        """
        from app.core.celery_app import celery_app as _celery

        REQUIRED_TASKS = [
            "app.erp.ERPCoach.tasks.erp_checkins.dispatch_due_checkins",
            "app.erp.ERPCoach.tasks.erp_checkins.run_checkin",
            "app.erp.ERPCoach.tasks.erp_reports.run_end_session_report",
        ]

        # --- ping workers (2 s timeout) ---
        ping_result = _celery.control.ping(timeout=2) or []
        workers_alive = [list(w.keys())[0] for w in ping_result if w]

        if not workers_alive:
            return JSONResponse(
                status_code=503,
                content={
                    "celery": "offline",
                    "workers": [],
                    "tasks_registered": False,
                    "detail": "No Celery workers responded to ping. Is the worker running?",
                },
            )

        # --- inspect registered tasks ---
        inspector = _celery.control.inspect(workers_alive, timeout=2)
        registered_map = inspector.registered() or {}

        all_registered: set[str] = set()
        for task_list in registered_map.values():
            all_registered.update(task_list or [])

        missing = [t for t in REQUIRED_TASKS if t not in all_registered]
        tasks_ok = len(missing) == 0

        return JSONResponse(
            status_code=200 if tasks_ok else 206,
            content={
                "celery": "ok" if tasks_ok else "degraded",
                "workers": workers_alive,
                "tasks_registered": tasks_ok,
                "missing_tasks": missing,
                "all_erp_tasks": [t for t in sorted(all_registered) if "erp" in t.lower()],
            },
        )

    @app.get("/health/imaginal-generator", tags=["health"])
    def imaginal_generator_health():
        graph_ready = hasattr(app.state, "imaginal_graph")
        checkpointer_ready = hasattr(app.state, "imaginal_checkpointer_cm")

        return {
            "imaginal_generator": "ok" if graph_ready and checkpointer_ready else "not_ready",
            "graph_ready": graph_ready,
            "checkpointer_ready": checkpointer_ready,
        }

    # Optional startup hook (useful if you want to auto-create tables in dev)
    # @app.on_event("startup")
    # def on_startup():
    #     Base.metadata.create_all(bind=engine)

    return app


app = create_app()
