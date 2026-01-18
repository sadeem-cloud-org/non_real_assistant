"""
Migration script to add WAHA sessions and notification preferences

Run this script to update the database:
    python migrations/add_waha_and_notification_prefs.py [database_path]

If database_path is not provided, it will try to:
1. Use DATABASE_URL from .env file
2. Default to 'database.db' in the current directory
"""

import sys
import os
import sqlite3

# Try to get database path from environment
def get_database_path():
    """Get database path from various sources"""

    # If provided as argument
    if len(sys.argv) > 1:
        return sys.argv[1]

    # Check DATABASE_URL environment variable first (for Docker)
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        # Handle sqlite:/// and sqlite://// (absolute path) formats
        if db_url.startswith('sqlite:////'):
            # Absolute path: sqlite:////app/data/database.db -> /app/data/database.db
            return db_url.replace('sqlite:///', '')
        elif db_url.startswith('sqlite:///'):
            # Relative path: sqlite:///database.db -> database.db
            return db_url.replace('sqlite:///', '')

    # Try to load from .env
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_file = os.path.join(project_dir, '.env')

    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                if line.strip().startswith('DATABASE_URL='):
                    db_url = line.strip().split('=', 1)[1].strip('"\'')
                    # Handle sqlite:/// and sqlite://// formats
                    if db_url.startswith('sqlite:////'):
                        return db_url.replace('sqlite:///', '')
                    elif db_url.startswith('sqlite:///'):
                        return db_url.replace('sqlite:///', '')

    # Try default locations (including Docker paths)
    default_paths = [
        '/app/data/database.db',  # Docker volume path
        os.path.join(project_dir, 'data', 'database.db'),
        os.path.join(project_dir, 'database.db'),
        os.path.join(project_dir, 'instance', 'database.db'),
        'database.db'
    ]

    for path in default_paths:
        if os.path.exists(path):
            return path

    # Return default
    return os.path.join(project_dir, 'database.db')


def run_migration(db_path):
    """Run the migration to add new columns and tables"""

    print(f"Database path: {db_path}")
    print(f"File exists: {os.path.exists(db_path)}")

    if not os.path.exists(db_path):
        print(f"\nERROR: Database file does not exist at {db_path}")
        print("Please provide the correct path as an argument:")
        print("    python migrations/add_waha_and_notification_prefs.py /path/to/database.db")
        return False

    # Show file info
    file_size = os.path.getsize(db_path)
    print(f"File size: {file_size} bytes")

    if file_size == 0:
        print("\nERROR: Database file is empty!")
        return False

    print("\nStarting migration...")

    # Connect to SQLite database
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    try:
        # List existing tables for debugging
        print("\nExisting tables in database:")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()
        if tables:
            for table in tables:
                print(f"   - {table[0]}")
        else:
            print("   (no tables found - database may be empty)")

        # Check if users table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        users_table_exists = cursor.fetchone() is not None

        if not users_table_exists:
            print("\nWARNING: 'users' table does not exist!")
            print("This database may be empty or not the production database.")
            print("Skipping user columns migration...")

        # 1. Add new columns to users table (only if it exists)
        print("\n1. Adding new columns to users table...")

        user_columns = [
            ("whatsapp_number", "VARCHAR(20)"),
            ("telegram_notify", "BOOLEAN DEFAULT 1"),  # TRUE = 1 in SQLite
            ("email_notify", "BOOLEAN DEFAULT 0"),     # FALSE = 0 in SQLite
            ("whatsapp_notify", "BOOLEAN DEFAULT 0"),
        ]

        if users_table_exists:
            for column_name, column_type in user_columns:
                try:
                    cursor.execute(f"ALTER TABLE users ADD COLUMN {column_name} {column_type}")
                    connection.commit()
                    print(f"   + Added column: users.{column_name}")
                except sqlite3.OperationalError as e:
                    if "duplicate column" in str(e).lower():
                        print(f"   - Column users.{column_name} already exists")
                    else:
                        print(f"   ! Error adding users.{column_name}: {e}")
        else:
            print("   (skipped - users table not found)")

        # 2. Create waha_sessions table
        print("\n2. Creating waha_sessions table...")

        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS waha_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(100) NOT NULL,
                    session_name VARCHAR(100) NOT NULL UNIQUE,
                    api_url VARCHAR(500) NOT NULL,
                    api_key VARCHAR(255),
                    is_default BOOLEAN DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1,
                    webhook_enabled BOOLEAN DEFAULT 0,
                    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                    create_user_id INTEGER REFERENCES users(id)
                )
            """)
            connection.commit()
            print("   + Created table: waha_sessions")
        except sqlite3.OperationalError as e:
            if "already exists" in str(e).lower():
                print("   - Table waha_sessions already exists")
            else:
                print(f"   ! Error creating waha_sessions: {e}")

        # 3. Set default values for existing users
        print("\n3. Setting default values for existing users...")

        if users_table_exists:
            try:
                cursor.execute("""
                    UPDATE users
                    SET telegram_notify = 1
                    WHERE telegram_notify IS NULL
                """)
                connection.commit()
                print("   + Set telegram_notify = TRUE for existing users")
            except Exception as e:
                print(f"   - Could not update telegram_notify: {e}")

            try:
                cursor.execute("""
                    UPDATE users
                    SET email_notify = 0
                    WHERE email_notify IS NULL
                """)
                connection.commit()
                print("   + Set email_notify = FALSE for existing users")
            except Exception as e:
                print(f"   - Could not update email_notify: {e}")

            try:
                cursor.execute("""
                    UPDATE users
                    SET whatsapp_notify = 0
                    WHERE whatsapp_notify IS NULL
                """)
                connection.commit()
                print("   + Set whatsapp_notify = FALSE for existing users")
            except Exception as e:
                print(f"   - Could not update whatsapp_notify: {e}")
        else:
            print("   (skipped - users table not found)")

        print("\n" + "="*50)
        print("Migration completed successfully!")
        print("="*50)

    except Exception as e:
        print(f"\nMigration failed: {e}")
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


if __name__ == '__main__':
    db_path = get_database_path()
    run_migration(db_path)
