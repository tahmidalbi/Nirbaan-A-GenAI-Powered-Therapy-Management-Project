from app.database.session import engine
from sqlalchemy import text

def add_new_intake_columns():
    """Add affected_life_areas and other_conditions columns"""
    print("Adding new columns to patient_intakes table...")
    
    with engine.begin() as conn:
        # Add affected_life_areas column
        try:
            conn.execute(text(
                "ALTER TABLE patient_intakes ADD COLUMN IF NOT EXISTS affected_life_areas TEXT"
            ))
            print("✅ Added affected_life_areas column")
        except Exception as e:
            print(f"Note: {e}")
        
        # Add other_conditions column
        try:
            conn.execute(text(
                "ALTER TABLE patient_intakes ADD COLUMN IF NOT EXISTS other_conditions TEXT"
            ))
            print("✅ Added other_conditions column")
        except Exception as e:
            print(f"Note: {e}")
    
    print("\n✅ Database schema updated successfully!")

if __name__ == "__main__":
    add_new_intake_columns()
