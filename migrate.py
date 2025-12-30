#!/usr/bin/env python3
"""
Database migration script
Updates the database schema with new tables
Usage: python migrate.py
"""

from app import app
from models import db


def migrate():
    """Create or update all database tables"""
    with app.app_context():
        print("🔄 Starting database migration...")

        try:
            # إنشاء أو تحديث الجداول
            db.create_all()

            print("\n✅ Migration completed successfully!")
            print("\n📊 Tables created/updated:")
            print("   - users")
            print("   - otps")
            print("   - assistant_types")
            print("   - actions")
            print("   - assistants")
            print("   - tasks")
            print("   - action_executions")

            print("\n💡 Next steps:")
            print("   1. Run: python seed_assistant.py")
            print("      (to add example reminder assistant)")
            print("   2. Start the app: python app.py")

        except Exception as e:
            print(f"\n❌ Migration failed: {e}")
            return False

        return True


if __name__ == '__main__':
    migrate()