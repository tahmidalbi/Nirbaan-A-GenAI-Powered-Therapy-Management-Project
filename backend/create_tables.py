from app.database.session import engine
from app.database.base import Base
from app.users.models import User
from app.therapists.models import Therapist
from app.patients.models import Patient
from app.emergency_personnel.models import EmergencyPersonnel
from app.therapy_sessions.models import TherapySession

# Import all models before creating tables
Base.metadata.create_all(bind=engine)

print("✅ Database tables created successfully")
print("✅ Tables: users, therapists, patients, emergency_personnel, therapy_sessions")
