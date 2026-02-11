"""
Migration Script: Update therapist_notes table schema
- Drops old 'last_week_note' column
- Adds new 'week_notes' JSON column
- This allows storing notes for each week individually
"""
import sys
import os
from sqlalchemy import text

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database.session import engine

def migrate_therapist_notes():
    """Migrate therapist_notes table from last_week_note to week_notes"""
    
    print("Starting migration of therapist_notes table...")
    
    with engine.connect() as conn:
        try:
            # Check if week_notes column exists
            check_column_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='therapist_notes' AND column_name='week_notes'
            """)
            result = conn.execute(check_column_query)
            week_notes_exists = result.fetchone() is not None
            
            if week_notes_exists:
                print("✓ week_notes column already exists. Skipping migration.")
                return
            
            # Backup existing data
            print("1. Backing up existing notes data...")
            backup_query = text("""
                SELECT id, patient_id, therapist_id, last_week_note, created_at, updated_at
                FROM therapist_notes
            """)
            backup_data = conn.execute(backup_query).fetchall()
            print(f"   Backed up {len(backup_data)} records")
            
            # Add week_notes column
            print("2. Adding week_notes JSON column...")
            add_column_query = text("""
                ALTER TABLE therapist_notes 
                ADD COLUMN week_notes JSON DEFAULT '{}'::json
            """)
            conn.execute(add_column_query)
            print("   ✓ week_notes column added")
            
            # Migrate existing notes to week_notes JSON format
            if backup_data:
                print("3. Migrating existing notes to new format...")
                for row in backup_data:
                    note_id, patient_id, therapist_id, last_week_note, created_at, updated_at = row
                    if last_week_note:
                        # Move the last note to 'initial' key in week_notes
                        migrate_query = text("""
                            UPDATE therapist_notes
                            SET week_notes = jsonb_build_object('initial', :note)
                            WHERE id = :note_id
                        """)
                        conn.execute(migrate_query, {"note": last_week_note, "note_id": note_id})
                print(f"   ✓ Migrated {len(backup_data)} records")
            
            # Drop old column
            print("4. Dropping old last_week_note column...")
            drop_column_query = text("""
                ALTER TABLE therapist_notes 
                DROP COLUMN last_week_note
            """)
            conn.execute(drop_column_query)
            print("   ✓ last_week_note column dropped")
            
            # Commit the transaction
            conn.commit()
            
            print("\n✅ Migration completed successfully!")
            print("   - Old column 'last_week_note' removed")
            print("   - New column 'week_notes' added")
            print("   - Existing data migrated to 'initial' key")
            
        except Exception as e:
            print(f"\n❌ Migration failed: {str(e)}")
            conn.rollback()
            raise

def verify_migration():
    """Verify the migration was successful"""
    print("\nVerifying migration...")
    
    with engine.connect() as conn:
        # Check table structure
        check_query = text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name='therapist_notes'
            ORDER BY ordinal_position
        """)
        columns = conn.execute(check_query).fetchall()
        
        print("\nCurrent therapist_notes table structure:")
        for col_name, data_type in columns:
            print(f"   - {col_name}: {data_type}")
        
        # Check if we have data
        count_query = text("SELECT COUNT(*) FROM therapist_notes")
        count = conn.execute(count_query).scalar()
        print(f"\nTotal records in table: {count}")
        
        if count > 0:
            # Show sample data
            sample_query = text("""
                SELECT id, patient_id, week_notes 
                FROM therapist_notes 
                LIMIT 3
            """)
            samples = conn.execute(sample_query).fetchall()
            print("\nSample records:")
            for record in samples:
                print(f"   ID: {record[0]}, Patient: {record[1]}, Week Notes: {record[2]}")

if __name__ == "__main__":
    print("=" * 60)
    print("THERAPIST NOTES MIGRATION SCRIPT")
    print("=" * 60)
    print()
    
    try:
        migrate_therapist_notes()
        verify_migration()
        print("\n" + "=" * 60)
        print("Migration process completed!")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ Fatal error: {str(e)}")
        sys.exit(1)
