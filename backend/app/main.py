from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.router import router as auth_router
from app.patients.router import router as patients_router
from app.emergency_personnel.router import router as emergency_personnel_router

app = FastAPI(
    title="Nirbaan - Therapy Management Backend",
    version="0.1.0",
    description="Multi-tenant therapy management platform with JWT authentication"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(patients_router)
app.include_router(emergency_personnel_router)

@app.get("/")
def health_check():
    return {
        "status": "Backend running",
        "message": "Nirbaan Therapy Management API",
        "version": "0.1.0"
    }
