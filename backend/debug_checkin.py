"""One-off debug script — safe to delete after use."""
from app.database.session import SessionLocal
from sqlalchemy import text
from datetime import datetime, timedelta

db = SessionLocal()

r = db.execute(text(
    "SELECT id, status, last_checkin_at, last_agent_run_at, last_suds_at, "
    "created_at, resumed_at FROM erp_live_sessions WHERE id = 25"
)).fetchone()

print("=== Session 25 ===")
print("status:", r[1])
print("last_checkin_at:", r[2])
print("last_agent_run_at:", r[3])
print("last_suds_at:", r[4])
print("created_at:", r[5])
print("resumed_at:", r[6])

msgs = db.execute(text(
    "SELECT role, LEFT(content, 80), created_at "
    "FROM erp_chat_messages WHERE session_id = 25 ORDER BY created_at DESC LIMIT 5"
)).fetchall()
print("\nRecent messages:")
for m in msgs:
    print(f"  [{m[0]}] {m[1]} | {m[2]}")

patient_msg = db.execute(text(
    "SELECT created_at FROM erp_chat_messages "
    "WHERE session_id = 25 AND role = 'patient' ORDER BY created_at DESC LIMIT 1"
)).fetchone()
print("\nLast patient msg at:", patient_msg[0] if patient_msg else "None")

# Simulate what dispatch_due_checkins does
from app.erp.services.coach_storage import CoachStorage
storage = CoachStorage(db)
due = storage.find_running_sessions_due_for_checkin(checkin_seconds=120, limit=500)
print("\nSessions due for check-in (checkin_seconds=120):", due)

due5 = storage.find_running_sessions_due_for_checkin(checkin_seconds=300, limit=500)
print("Sessions due for check-in (checkin_seconds=300):", due5)

print("\nNow UTC:", datetime.utcnow())

db.close()
