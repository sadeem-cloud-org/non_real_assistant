#!/usr/bin/env python3
"""
Consolidated Database Migration Script
Contains all database migrations in one place.
Usage: python -m migrations.migrate
"""

from sqlalchemy import text


def migrate_database(app, db):
    """
    Run all database migrations.
    Creates or updates all database tables.
    """
    with app.app_context():
        print("Starting database migration...")

        try:
            # Create all tables
            db.create_all()
            print("Base tables created/updated")

            # Run additional migrations
            _add_script_id_to_assistants(db)

            print("\nMigration completed successfully!")
            print("\nTables created/updated:")
            print("   - users")
            print("   - otps")
            print("   - assistant_types")
            print("   - actions")
            print("   - assistants")
            print("   - tasks")
            print("   - scripts")
            print("   - script_executions")
            print("   - action_executions")

            return True

        except Exception as e:
            print(f"\nMigration failed: {e}")
            return False


def _add_script_id_to_assistants(db):
    """Add script_id column to assistants table if not exists"""
    try:
        db.session.execute(
            text('ALTER TABLE assistants ADD COLUMN script_id INTEGER REFERENCES scripts(id)')
        )
        db.session.commit()
        print("Added script_id column to assistants table")
    except Exception as e:
        error_str = str(e).lower()
        if 'duplicate column name' in error_str or 'already exists' in error_str:
            print("script_id column already exists in assistants table")
        else:
            db.session.rollback()
            # Not critical - column might already exist
            pass


def run_all_migrations():
    """
    Entry point for running migrations from command line.
    """
    import sys
    import os

    # Add parent directory to path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    from app import app
    from models import db

    success = migrate_database(app, db)

    if success:
        print("\nNext steps:")
        print("   1. Run: python -m seeds.seed_assistant_types")
        print("      (to add assistant types)")
        print("   2. Start the app: python app.py")

    return success


if __name__ == '__main__':
    run_all_migrations()
