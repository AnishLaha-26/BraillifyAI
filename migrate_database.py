#!/usr/bin/env python3
"""
Database migration script for BraillifyAI
Adds new fields to the Upload table for the complete pipeline
"""

import sqlite3
import os
from datetime import datetime

def get_database_path():
    """Get the path to the SQLite database"""
    # Common locations for Flask SQLite databases
    possible_paths = [
        'instance/braillify.db',  # Most likely location
        'instance/database.db',
        'app.db',
        'braillify.db',
        'instance/app.db'
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            print(f"✅ Found database: {path}")
            return path
    
    # If none found, create in instance directory
    os.makedirs('instance', exist_ok=True)
    return 'instance/database.db'

def check_column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns

def migrate_database():
    """Run database migration to add new fields"""
    db_path = get_database_path()
    print(f"📁 Database path: {db_path}")
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("🔍 Checking current database schema...")
    
    # Check if upload table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='upload'")
    if not cursor.fetchone():
        print("❌ Upload table doesn't exist. Please run Flask db init first.")
        return False
    
    # List of new columns to add
    new_columns = [
        ('optimization_model', 'VARCHAR(100)'),
        ('braille_content', 'TEXT'),
        ('pdf_path', 'VARCHAR(512)'),
        ('preview_pdf_path', 'VARCHAR(512)'),
        ('pdf_generation_date', 'DATETIME')
    ]
    
    migrations_applied = 0
    
    for column_name, column_type in new_columns:
        if not check_column_exists(cursor, 'upload', column_name):
            print(f"➕ Adding column: {column_name}")
            try:
                cursor.execute(f"ALTER TABLE upload ADD COLUMN {column_name} {column_type}")
                migrations_applied += 1
            except sqlite3.Error as e:
                print(f"❌ Error adding {column_name}: {e}")
        else:
            print(f"✅ Column {column_name} already exists")
    
    # Commit changes
    conn.commit()
    conn.close()
    
    print(f"\n🎉 Migration complete! {migrations_applied} columns added.")
    return True

def verify_schema():
    """Verify the database schema after migration"""
    db_path = get_database_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("\n🔍 Verifying database schema...")
    cursor.execute("PRAGMA table_info(upload)")
    columns = cursor.fetchall()
    
    print("📋 Current upload table columns:")
    for col in columns:
        print(f"  - {col[1]} ({col[2]})")
    
    # Check for our new columns
    column_names = [col[1] for col in columns]
    required_columns = [
        'optimization_model',
        'braille_content', 
        'pdf_path',
        'preview_pdf_path',
        'pdf_generation_date'
    ]
    
    missing_columns = [col for col in required_columns if col not in column_names]
    
    if missing_columns:
        print(f"⚠️ Missing columns: {missing_columns}")
        return False
    else:
        print("✅ All required columns present!")
        return True

if __name__ == "__main__":
    print("🚀 BraillifyAI Database Migration")
    print("=" * 50)
    print(f"🕐 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run migration
    success = migrate_database()
    
    if success:
        # Verify schema
        verify_schema()
        print("\n✅ Database migration completed successfully!")
        print("🎯 You can now upload files without errors.")
    else:
        print("\n❌ Database migration failed!")
        print("Please check your Flask database setup.")
    
    print(f"🕐 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
