"""
Migration script to add WAHA sessions and notification preferences

Run this script to update the database:
    python migrations/add_waha_and_notification_prefs.py
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from models import db


def run_migration():
    """Run the migration to add new columns and tables"""

    with app.app_context():
        print("Starting migration...")

        # Get database connection
        connection = db.engine.connect()

        try:
            # 1. Add new columns to users table
            print("\n1. Adding new columns to users table...")

            user_columns = [
                ("whatsapp_number", "VARCHAR(20)"),
                ("telegram_notify", "BOOLEAN DEFAULT TRUE"),
                ("email_notify", "BOOLEAN DEFAULT FALSE"),
                ("whatsapp_notify", "BOOLEAN DEFAULT FALSE"),
            ]

            for column_name, column_type in user_columns:
                try:
                    connection.execute(db.text(
                        f"ALTER TABLE users ADD COLUMN {column_name} {column_type}"
                    ))
                    connection.commit()
                    print(f"   ✓ Added column: users.{column_name}")
                except Exception as e:
                    if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                        print(f"   - Column users.{column_name} already exists")
                    else:
                        print(f"   ✗ Error adding users.{column_name}: {e}")

            # 2. Create waha_sessions table
            print("\n2. Creating waha_sessions table...")

            try:
                connection.execute(db.text("""
                    CREATE TABLE IF NOT EXISTS waha_sessions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name VARCHAR(100) NOT NULL,
                        session_name VARCHAR(100) NOT NULL UNIQUE,
                        api_url VARCHAR(500) NOT NULL,
                        api_key VARCHAR(255),
                        is_default BOOLEAN DEFAULT FALSE,
                        is_active BOOLEAN DEFAULT TRUE,
                        webhook_enabled BOOLEAN DEFAULT FALSE,
                        create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                        create_user_id INTEGER REFERENCES users(id)
                    )
                """))
                connection.commit()
                print("   ✓ Created table: waha_sessions")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print("   - Table waha_sessions already exists")
                else:
                    print(f"   ✗ Error creating waha_sessions: {e}")

            # 3. Set default values for existing users
            print("\n3. Setting default values for existing users...")

            try:
                connection.execute(db.text("""
                    UPDATE users
                    SET telegram_notify = TRUE
                    WHERE telegram_notify IS NULL
                """))
                connection.commit()
                print("   ✓ Set telegram_notify = TRUE for existing users")
            except Exception as e:
                print(f"   - Could not update telegram_notify: {e}")

            try:
                connection.execute(db.text("""
                    UPDATE users
                    SET email_notify = FALSE
                    WHERE email_notify IS NULL
                """))
                connection.commit()
                print("   ✓ Set email_notify = FALSE for existing users")
            except Exception as e:
                print(f"   - Could not update email_notify: {e}")

            try:
                connection.execute(db.text("""
                    UPDATE users
                    SET whatsapp_notify = FALSE
                    WHERE whatsapp_notify IS NULL
                """))
                connection.commit()
                print("   ✓ Set whatsapp_notify = FALSE for existing users")
            except Exception as e:
                print(f"   - Could not update whatsapp_notify: {e}")

            print("\n" + "="*50)
            print("Migration completed successfully!")
            print("="*50)

        except Exception as e:
            print(f"\nMigration failed: {e}")
            raise
        finally:
            connection.close()


if __name__ == '__main__':
    run_migration()
