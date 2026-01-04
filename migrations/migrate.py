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
            _add_user_profile_fields(db)
            _add_script_notification_fields(db)
            _add_execution_share_fields(db)
            _add_assistant_type_fields(db)

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
            print("   - system_settings")

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


def _add_user_profile_fields(db):
    """Add new user profile fields"""
    columns = [
        ('name', 'VARCHAR(100)'),
        ('email', 'VARCHAR(200)'),
        ('language', "VARCHAR(10) DEFAULT 'ar'"),
        ('timezone', "VARCHAR(50) DEFAULT 'Africa/Cairo'"),
        ('notify_telegram', 'BOOLEAN DEFAULT 1'),
        ('notify_email', 'BOOLEAN DEFAULT 0'),
        ('notify_browser', 'BOOLEAN DEFAULT 1'),
        ('settings', 'TEXT'),
    ]

    for col_name, col_type in columns:
        try:
            db.session.execute(
                text(f'ALTER TABLE users ADD COLUMN {col_name} {col_type}')
            )
            db.session.commit()
            print(f"Added {col_name} column to users table")
        except Exception as e:
            db.session.rollback()
            error_str = str(e).lower()
            if 'duplicate column name' in error_str or 'already exists' in error_str:
                pass  # Column already exists


def _add_script_notification_fields(db):
    """Add notification fields to scripts table"""
    columns = [
        ('send_output_telegram', 'BOOLEAN DEFAULT 0'),
        ('send_output_email', 'BOOLEAN DEFAULT 0'),
    ]

    for col_name, col_type in columns:
        try:
            db.session.execute(
                text(f'ALTER TABLE scripts ADD COLUMN {col_name} {col_type}')
            )
            db.session.commit()
            print(f"Added {col_name} column to scripts table")
        except Exception as e:
            db.session.rollback()
            error_str = str(e).lower()
            if 'duplicate column name' in error_str or 'already exists' in error_str:
                pass


def _add_execution_share_fields(db):
    """Add sharing fields to execution tables"""
    # Script executions
    script_exec_columns = [
        ('share_token', 'VARCHAR(64) UNIQUE'),
        ('is_public', 'BOOLEAN DEFAULT 0'),
        ('telegram_sent', 'BOOLEAN DEFAULT 0'),
        ('email_sent', 'BOOLEAN DEFAULT 0'),
    ]

    for col_name, col_type in script_exec_columns:
        try:
            db.session.execute(
                text(f'ALTER TABLE script_executions ADD COLUMN {col_name} {col_type}')
            )
            db.session.commit()
            print(f"Added {col_name} column to script_executions table")
        except Exception as e:
            db.session.rollback()
            error_str = str(e).lower()
            if 'duplicate column name' in error_str or 'already exists' in error_str:
                pass

    # Action executions
    action_exec_columns = [
        ('share_token', 'VARCHAR(64) UNIQUE'),
        ('is_public', 'BOOLEAN DEFAULT 0'),
    ]

    for col_name, col_type in action_exec_columns:
        try:
            db.session.execute(
                text(f'ALTER TABLE action_executions ADD COLUMN {col_name} {col_type}')
            )
            db.session.commit()
            print(f"Added {col_name} column to action_executions table")
        except Exception as e:
            db.session.rollback()
            error_str = str(e).lower()
            if 'duplicate column name' in error_str or 'already exists' in error_str:
                pass


def _add_assistant_type_fields(db):
    """Add new fields to assistant_types table"""
    columns = [
        ('description_ar', 'TEXT'),
        ('description_en', 'TEXT'),
        ('color', "VARCHAR(20) DEFAULT 'blue'"),
        ('default_settings', 'TEXT'),
    ]

    for col_name, col_type in columns:
        try:
            db.session.execute(
                text(f'ALTER TABLE assistant_types ADD COLUMN {col_name} {col_type}')
            )
            db.session.commit()
            print(f"Added {col_name} column to assistant_types table")
        except Exception as e:
            db.session.rollback()
            error_str = str(e).lower()
            if 'duplicate column name' in error_str or 'already exists' in error_str:
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
