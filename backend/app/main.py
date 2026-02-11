from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.router import router as auth_router
from app.patients.router import router as patients_router
from app.emergency_personnel.router import router as emergency_personnel_router
from app.resources.router import router as resources_router  # NEW
from app.progress.router import router as progress_router
from app.sessions.router import router as sessions_router

app = FastAPI(
    title="Nirbaan - Therapy Management Backend",
    version="0.1.0",
    description="Multi-tenant therapy management platform with JWT authentication and RAG"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(patients_router)
app.include_router(emergency_personnel_router)
app.include_router(resources_router)  # --> /resources/*
app.include_router(progress_router)  # --> /progress/*
app.include_router(sessions_router)  # --> /sessions/*

@app.get("/")
def health_check():
    return {
        "status": "Backend running",
        "message": "Nirbaan Therapy Management API with RAG",
        "version": "0.1.0"
    }