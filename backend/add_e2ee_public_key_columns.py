"""
Migration: Add public_key_jwk TEXT column to patients and emergency_personnel.
These columns store each user's ECDH P-256 public key (JWK format) for end-to-end
encrypted EP-Patient direct chat. The server stores the public key only — private
keys never leave the user's browser (stored in IndexedDB).
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database.session import SessionLocal
from sqlalchemy import text


def main():
    db = SessionLocal()
    try:
        for table in ("patients", "emergency_personnel"):
            try:
                db.execute(text(f"ALTER TABLE {table} ADD COLUMN public_key_jwk TEXT"))
                db.commit()
                print(f"✅ Added public_key_jwk to {table}")
            except Exception as e:
                db.rollback()
                msg = str(e).lower()
                if "already exists" in msg or "duplicate column" in msg:
                    print(f"ℹ️  public_key_jwk already exists in {table}, skipping")
                else:
                    raise
        print("✅ Migration complete")
    finally:
        db.close()


if __name__ == "__main__":
    main()
