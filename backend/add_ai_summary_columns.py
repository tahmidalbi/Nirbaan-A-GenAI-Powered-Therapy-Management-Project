"""
Migration script to add AI summary columns to patient_intakes table.
Run this once: python add_ai_summary_columns.py
"""
import os
import sys
from pathlib import Path

# Add backend directory to path so we can import app modules
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine, text
from app.core.config import settings


def add_ai_summary_columns():
    """Add AI summary columns to patient_intakes table"""
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        print("Adding AI summary columns to patient_intakes table...")
        
        try:
            # Add ai_summary_status column
            conn.execute(text("""
                ALTER TABLE patient_intakes 
                ADD COLUMN IF NOT EXISTS ai_summary_status VARCHAR(20) NOT NULL DEFAULT 'pending'
            """))
            print("✅ Added ai_summary_status column")
            
            # Add ai_summary_text column
            conn.execute(text("""
                ALTER TABLE patient_intakes 
                ADD COLUMN IF NOT EXISTS ai_summary_text TEXT
            """))
            print("✅ Added ai_summary_text column")
            
            # Add ai_summary_structured column
            conn.execute(text("""
                ALTER TABLE patient_intakes 
                ADD COLUMN IF NOT EXISTS ai_summary_structured JSONB
            """))
            print("✅ Added ai_summary_structured column")
            
            # Add ai_summary_error column
            conn.execute(text("""
                ALTER TABLE patient_intakes 
                ADD COLUMN IF NOT EXISTS ai_summary_error TEXT
            """))
            print("✅ Added ai_summary_error column")
            
            # Add ai_summary_version column
            conn.execute(text("""
                ALTER TABLE patient_intakes 
                ADD COLUMN IF NOT EXISTS ai_summary_version INTEGER NOT NULL DEFAULT 1
            """))
            print("✅ Added ai_summary_version column")
            
            # Add ai_summary_updated_at column
            conn.execute(text("""
                ALTER TABLE patient_intakes 
                ADD COLUMN IF NOT EXISTS ai_summary_updated_at TIMESTAMP
            """))
            print("✅ Added ai_summary_updated_at column")
            
            # Create index on ai_summary_status for faster queries
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_patient_intakes_ai_summary_status 
                ON patient_intakes(ai_summary_status)
            """))
            print("✅ Created index on ai_summary_status")
            
            conn.commit()
            print("\n✅ Database schema updated successfully!")
            print("AI summary columns are now available in patient_intakes table.")
            
        except Exception as e:
            print(f"\n❌ Error updating database schema: {e}")
            conn.rollback()
            raise


if __name__ == "__main__":
    add_ai_summary_columns()
