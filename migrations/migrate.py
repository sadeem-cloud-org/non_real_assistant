#!/usr/bin/env python3
"""
Database Migration Script
Creates and updates all database tables.
Usage: python -m migrations.migrate
"""

from sqlalchemy import text, inspect


def migrate_database(app, db):
    """
    Run all database migrations.
    """
    with app.app_context():
        print("Starting database migration...")

        try:
            # Check if we need to handle old schema
            _handle_schema_migration(db)

            # Create all tables from models
            db.create_all()
            print("Base tables created/updated")

            # Seed default languages
            _seed_languages(db)

            print("\nMigration completed successfully!")
            print("\nTables created/updated:")
            print("   - languages")
            print("   - system_settings")
            print("   - users")
            print("   - user_login_history")
            print("   - otps")
            print("   - notify_templates")
            print("   - assistant_types")
            print("   - assistants")
            print("   - tasks")
            print("   - task_attachments")
            print("   - ssh_servers")
            print("   - scripts")
            print("   - script_execute_logs")

            return True

        except Exception as e:
            print(f"\nMigration failed: {e}")
            import traceback
            traceback.print_exc()
            return False


def _handle_schema_migration(db):
    """Handle migration from old schema to new schema"""
    inspector = inspect(db.engine)
    existing_tables = inspector.get_table_names()

    # Tables that need to be dropped and recreated due to schema changes
    tables_to_recreate = []

    # Add new columns to tasks table for sharing feature
    if 'tasks' in existing_tables:
        columns = [c['name'] for c in inspector.get_columns('tasks')]

        # Add share_token column if missing
        if 'share_token' not in columns:
            try:
                db.session.execute(text('ALTER TABLE tasks ADD COLUMN share_token VARCHAR(64)'))
                db.session.commit()
                print("Added share_token column to tasks table")
            except Exception as e:
                print(f"Could not add share_token column: {e}")

        # Add is_public column if missing
        if 'is_public' not in columns:
            try:
                db.session.execute(text('ALTER TABLE tasks ADD COLUMN is_public BOOLEAN DEFAULT 0'))
                db.session.commit()
                print("Added is_public column to tasks table")
            except Exception as e:
                print(f"Could not add is_public column: {e}")

    # Add new columns to script_execute_logs table for sharing feature
    if 'script_execute_logs' in existing_tables:
        columns = [c['name'] for c in inspector.get_columns('script_execute_logs')]

        # Add share_token column if missing
        if 'share_token' not in columns:
            try:
                db.session.execute(text('ALTER TABLE script_execute_logs ADD COLUMN share_token VARCHAR(64)'))
                db.session.commit()
                print("Added share_token column to script_execute_logs table")
            except Exception as e:
                print(f"Could not add share_token column: {e}")

        # Add is_public column if missing
        if 'is_public' not in columns:
            try:
                db.session.execute(text('ALTER TABLE script_execute_logs ADD COLUMN is_public BOOLEAN DEFAULT 0'))
                db.session.commit()
                print("Added is_public column to script_execute_logs table")
            except Exception as e:
                print(f"Could not add is_public column: {e}")

    # Add ssh_server_id column to scripts table
    if 'scripts' in existing_tables:
        columns = [c['name'] for c in inspector.get_columns('scripts')]
        if 'ssh_server_id' not in columns:
            try:
                db.session.execute(text('ALTER TABLE scripts ADD COLUMN ssh_server_id INTEGER REFERENCES ssh_servers(id)'))
                db.session.commit()
                print("Added ssh_server_id column to scripts table")
            except Exception as e:
                print(f"Could not add ssh_server_id column: {e}")

    # Check assistant_types table
    if 'assistant_types' in existing_tables:
        columns = [c['name'] for c in inspector.get_columns('assistant_types')]
        if 'create_time' not in columns or 'related_action' not in columns:
            tables_to_recreate.append('assistant_types')
            print("assistant_types table has old schema, will recreate")

    # Check tasks table
    if 'tasks' in existing_tables:
        columns = [c['name'] for c in inspector.get_columns('tasks')]
        if 'name' not in columns:
            tables_to_recreate.append('tasks')
            print("tasks table has old schema, will recreate")

    # Check users table for mobile column and language_id
    if 'users' in existing_tables:
        columns = [c['name'] for c in inspector.get_columns('users')]
        needs_recreate = False

        if 'language_id' not in columns or 'create_time' not in columns:
            needs_recreate = True

        if 'mobile' not in columns and 'phone' in columns:
            # Try to rename phone to mobile
            try:
                db.session.execute(text('ALTER TABLE users RENAME COLUMN phone TO mobile'))
                db.session.commit()
                print("Renamed users.phone to users.mobile")
            except Exception as e:
                print(f"Could not rename phone column: {e}")
                needs_recreate = True

        if needs_recreate:
            tables_to_recreate.append('users')
            print("users table has old schema, will recreate")

    # Check scripts table
    if 'scripts' in existing_tables:
        columns = [c['name'] for c in inspector.get_columns('scripts')]
        if 'create_user_id' not in columns:
            tables_to_recreate.append('scripts')
            print("scripts table has old schema, will recreate")

    # Check assistants table
    if 'assistants' in existing_tables:
        columns = [c['name'] for c in inspector.get_columns('assistants')]
        if 'create_time' not in columns or 'create_user_id' not in columns:
            tables_to_recreate.append('assistants')
            print("assistants table has old schema, will recreate")

    # Drop old tables that no longer exist in new schema
    old_tables = ['actions', 'action_executions', 'script_executions']
    for table in old_tables:
        if table in existing_tables:
            try:
                db.session.execute(text(f'DROP TABLE IF EXISTS {table}'))
                db.session.commit()
                print(f"Dropped old table: {table}")
            except Exception as e:
                print(f"Could not drop {table}: {e}")

    # Drop and recreate tables with changed schema
    # Note: This will delete data! In production, you'd migrate data first
    for table in tables_to_recreate:
        try:
            db.session.execute(text(f'DROP TABLE IF EXISTS {table}'))
            db.session.commit()
            print(f"Dropped table for recreation: {table}")
        except Exception as e:
            print(f"Could not drop {table}: {e}")


def _seed_languages(db):
    """Seed default languages if not exist"""
    from models import Language

    languages = [
        {'name': 'العربية', 'iso_code': 'ar'},
        {'name': 'English', 'iso_code': 'en'}
    ]

    for lang_data in languages:
        existing = Language.query.filter_by(iso_code=lang_data['iso_code']).first()
        if not existing:
            lang = Language(**lang_data)
            db.session.add(lang)
            print(f"Added language: {lang_data['name']}")

    db.session.commit()


def seed_assistant_types(db):
    """Seed default assistant types - only 2 types: task notifications and script execution"""
    from models import AssistantType

    # Only 2 assistant types as per user requirements
    types = [
        {'name': 'task_notify', 'related_action': 'task'},
        {'name': 'script_runner', 'related_action': 'script'}
    ]

    # Remove old types if they exist
    old_types = ['reminder', 'task_manager', 'server_monitor', 'automation', 'data_collector', 'notification', 'custom']
    for old_name in old_types:
        old_type = AssistantType.query.filter_by(name=old_name).first()
        if old_type:
            db.session.delete(old_type)
            print(f"Removed old assistant type: {old_name}")

    for type_data in types:
        existing = AssistantType.query.filter_by(name=type_data['name']).first()
        if not existing:
            assistant_type = AssistantType(**type_data)
            db.session.add(assistant_type)
            print(f"Added assistant type: {type_data['name']}")

    db.session.commit()


def seed_notify_templates(db):
    """Seed default notification templates"""
    from models import NotifyTemplate

    templates = [
        {
            'name': 'task_reminder',
            'text': '⏰ تذكير: {task_name}\n\n{description}\n\nالموعد: {time}'
        },
        {
            'name': 'task_completed',
            'text': '✅ تم إتمام المهمة: {task_name}'
        },
        {
            'name': 'script_success',
            'text': '✅ تم تنفيذ السكريبت: {script_name}\n\nالنتيجة:\n{output}'
        },
        {
            'name': 'script_failed',
            'text': '❌ فشل تنفيذ السكريبت: {script_name}\n\nالخطأ:\n{error}'
        },
        {
            'name': 'server_status',
            'text': '🖥️ حالة السيرفر: {server_name}\n\nالحالة: {status}\n{details}'
        }
    ]

    for template_data in templates:
        existing = NotifyTemplate.query.filter_by(name=template_data['name']).first()
        if not existing:
            template = NotifyTemplate(**template_data)
            db.session.add(template)
            print(f"Added notify template: {template_data['name']}")

    db.session.commit()


def load_translations_from_files(db):
    """Load translations from .po files automatically"""
    import os

    translations_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'translations')

    if not os.path.exists(translations_dir):
        print("No translations directory found")
        return

    from services.translation_service import TranslationService
    service = TranslationService()

    try:
        result = service.load_from_files(translations_dir)
        if result.get('success'):
            total_imported = sum(r.get('imported', 0) + r.get('updated', 0) for r in result.get('results', []))
            print(f"Loaded {total_imported} translations from files")
        else:
            print(f"Warning: Could not load translations: {result.get('error')}")
    except Exception as e:
        print(f"Warning: Could not load translations: {e}")


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
        # Seed assistant types and templates
        with app.app_context():
            seed_assistant_types(db)
            seed_notify_templates(db)
            # Load translations from .po files
            load_translations_from_files(db)

        print("\nNext steps:")
        print("   1. Create a user: python create_user.py create --phone 01234567890 --telegram_id YOUR_ID")
        print("   2. Start the app: python app.py")

    return success


if __name__ == '__main__':
    run_all_migrations()
