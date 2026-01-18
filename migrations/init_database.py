#!/usr/bin/env python3
"""
Complete Database Migration/Initialization Script

This script creates all database tables and adds default data.
It can be run on a fresh database or an existing one.

Usage:
    python migrations/init_database.py [database_path]

If database_path is not provided, it will auto-detect from:
1. DATABASE_URL environment variable
2. .env file
3. Default locations
"""

import sys
import os
import sqlite3


def get_database_path():
    """Get database path from various sources"""

    # If provided as argument
    if len(sys.argv) > 1:
        return sys.argv[1]

    # Check DATABASE_URL environment variable first (for Docker)
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        if db_url.startswith('sqlite:////'):
            return db_url.replace('sqlite:///', '')
        elif db_url.startswith('sqlite:///'):
            return db_url.replace('sqlite:///', '')

    # Try to load from .env
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_file = os.path.join(project_dir, '.env')

    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                if line.strip().startswith('DATABASE_URL='):
                    db_url = line.strip().split('=', 1)[1].strip('"\'')
                    if db_url.startswith('sqlite:////'):
                        return db_url.replace('sqlite:///', '')
                    elif db_url.startswith('sqlite:///'):
                        return db_url.replace('sqlite:///', '')

    # Try default locations
    default_paths = [
        '/app/data/database.db',
        os.path.join(project_dir, 'data', 'database.db'),
        os.path.join(project_dir, 'database.db'),
        os.path.join(project_dir, 'instance', 'database.db'),
    ]

    for path in default_paths:
        if os.path.exists(path):
            return path

    return os.path.join(project_dir, 'database.db')


def table_exists(cursor, table_name):
    """Check if a table exists"""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    return cursor.fetchone() is not None


def column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns


def add_column_if_not_exists(cursor, table_name, column_name, column_def):
    """Add a column to a table if it doesn't exist"""
    if not column_exists(cursor, table_name, column_name):
        try:
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}")
            print(f"   + Added column: {table_name}.{column_name}")
            return True
        except sqlite3.OperationalError as e:
            print(f"   ! Error adding {table_name}.{column_name}: {e}")
            return False
    else:
        print(f"   - Column {table_name}.{column_name} already exists")
        return False


def run_migration(db_path):
    """Run the complete database migration"""

    print("=" * 60)
    print("Non Real Assistant - Database Migration")
    print("=" * 60)
    print(f"\nDatabase path: {db_path}")
    print(f"File exists: {os.path.exists(db_path)}")

    # Create directory if needed
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
        print(f"Created directory: {db_dir}")

    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    try:
        # ============================================================
        # 1. LANGUAGES TABLE
        # ============================================================
        print("\n[1/14] Languages table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS languages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL,
                iso_code VARCHAR(10) UNIQUE NOT NULL,
                create_time DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        connection.commit()
        print("   ✓ languages table ready")

        # ============================================================
        # 2. TRANSLATIONS TABLE
        # ============================================================
        print("\n[2/14] Translations table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS translations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                language_id INTEGER NOT NULL REFERENCES languages(id),
                key VARCHAR(500) NOT NULL,
                value TEXT,
                context VARCHAR(200),
                create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                update_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(language_id, key)
            )
        """)
        connection.commit()
        print("   ✓ translations table ready")

        # ============================================================
        # 3. SYSTEM_SETTINGS TABLE
        # ============================================================
        print("\n[3/14] System settings table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_bot_token VARCHAR(200),
                otp_expiration_seconds INTEGER DEFAULT 300,
                default_language_id INTEGER REFERENCES languages(id),
                title VARCHAR(200) DEFAULT 'Non Real Assistant',
                logo BLOB
            )
        """)
        connection.commit()
        print("   ✓ system_settings table ready")

        # ============================================================
        # 4. KEY_VALUE_SETTINGS TABLE
        # ============================================================
        print("\n[4/14] Key-value settings table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS key_value_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key VARCHAR(100) UNIQUE NOT NULL,
                value TEXT,
                value_type VARCHAR(20) DEFAULT 'string'
            )
        """)
        connection.commit()
        print("   ✓ key_value_settings table ready")

        # ============================================================
        # 5. USERS TABLE
        # ============================================================
        print("\n[5/14] Users table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mobile VARCHAR(20) UNIQUE NOT NULL,
                name VARCHAR(100),
                avatar VARCHAR(255),
                telegram_id VARCHAR(50) UNIQUE,
                email VARCHAR(200),
                whatsapp_number VARCHAR(20),
                timezone VARCHAR(50) DEFAULT 'Africa/Cairo',
                language_id INTEGER REFERENCES languages(id),
                browser_notify BOOLEAN DEFAULT 1,
                telegram_notify BOOLEAN DEFAULT 1,
                telegram_bot_blocked BOOLEAN DEFAULT 0,
                email_notify BOOLEAN DEFAULT 0,
                whatsapp_notify BOOLEAN DEFAULT 0,
                is_admin BOOLEAN DEFAULT 0,
                create_time DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        connection.commit()

        # Add missing columns to users table (for existing databases)
        if table_exists(cursor, 'users'):
            add_column_if_not_exists(cursor, 'users', 'whatsapp_number', 'VARCHAR(20)')
            add_column_if_not_exists(cursor, 'users', 'telegram_notify', 'BOOLEAN DEFAULT 1')
            add_column_if_not_exists(cursor, 'users', 'telegram_bot_blocked', 'BOOLEAN DEFAULT 0')
            add_column_if_not_exists(cursor, 'users', 'email_notify', 'BOOLEAN DEFAULT 0')
            add_column_if_not_exists(cursor, 'users', 'whatsapp_notify', 'BOOLEAN DEFAULT 0')
            add_column_if_not_exists(cursor, 'users', 'browser_notify', 'BOOLEAN DEFAULT 1')
            connection.commit()
        print("   ✓ users table ready")

        # ============================================================
        # 6. USER_LOGIN_HISTORY TABLE
        # ============================================================
        print("\n[6/14] User login history table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_login_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                ip VARCHAR(50),
                browser VARCHAR(200),
                create_time DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        connection.commit()
        print("   ✓ user_login_history table ready")

        # ============================================================
        # 7. OTPS TABLE
        # ============================================================
        print("\n[7/14] OTPs table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS otps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                code VARCHAR(6) NOT NULL,
                create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                expires_at DATETIME NOT NULL,
                used BOOLEAN DEFAULT 0
            )
        """)
        connection.commit()
        print("   ✓ otps table ready")

        # ============================================================
        # 8. NOTIFY_TEMPLATES TABLE
        # ============================================================
        print("\n[8/14] Notification templates table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notify_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL,
                text TEXT NOT NULL
            )
        """)
        connection.commit()
        print("   ✓ notify_templates table ready")

        # ============================================================
        # 9. ASSISTANT_TYPES TABLE
        # ============================================================
        print("\n[9/14] Assistant types table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS assistant_types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) UNIQUE NOT NULL,
                create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                related_action VARCHAR(20) DEFAULT 'task'
            )
        """)
        connection.commit()
        print("   ✓ assistant_types table ready")

        # ============================================================
        # 10. ASSISTANTS TABLE
        # ============================================================
        print("\n[10/14] Assistants table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS assistants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(200) NOT NULL,
                create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                assistant_type_id INTEGER NOT NULL REFERENCES assistant_types(id),
                create_user_id INTEGER NOT NULL REFERENCES users(id),
                telegram_notify BOOLEAN DEFAULT 1,
                email_notify BOOLEAN DEFAULT 0,
                notify_template_id INTEGER REFERENCES notify_templates(id),
                run_every VARCHAR(20),
                next_run_time DATETIME
            )
        """)
        connection.commit()
        print("   ✓ assistants table ready")

        # ============================================================
        # 11. TASKS TABLE
        # ============================================================
        print("\n[11/14] Tasks table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(500) NOT NULL,
                create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                create_user_id INTEGER NOT NULL REFERENCES users(id),
                description TEXT,
                time DATETIME,
                complete_time DATETIME,
                cancel_time DATETIME,
                assistant_id INTEGER REFERENCES assistants(id),
                notify_sent BOOLEAN DEFAULT 0,
                share_token VARCHAR(64) UNIQUE,
                is_public BOOLEAN DEFAULT 0
            )
        """)
        connection.commit()
        print("   ✓ tasks table ready")

        # ============================================================
        # 12. TASK_ATTACHMENTS TABLE
        # ============================================================
        print("\n[12/14] Task attachments table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_attachments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL REFERENCES tasks(id),
                filename VARCHAR(255) NOT NULL,
                original_filename VARCHAR(255) NOT NULL,
                file_size INTEGER,
                mime_type VARCHAR(100),
                create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                uploaded_by INTEGER REFERENCES users(id)
            )
        """)
        connection.commit()
        print("   ✓ task_attachments table ready")

        # ============================================================
        # 13. SSH_SERVERS TABLE
        # ============================================================
        print("\n[13/14] SSH servers table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ssh_servers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(200) NOT NULL,
                host VARCHAR(255) NOT NULL,
                port INTEGER DEFAULT 22,
                username VARCHAR(100) NOT NULL,
                auth_type VARCHAR(20) DEFAULT 'password',
                password VARCHAR(255),
                private_key TEXT,
                is_active BOOLEAN DEFAULT 1,
                create_user_id INTEGER NOT NULL REFERENCES users(id),
                create_time DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        connection.commit()
        print("   ✓ ssh_servers table ready")

        # ============================================================
        # 14. SCRIPTS TABLE
        # ============================================================
        print("\n[14/14] Scripts and related tables...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scripts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(200) NOT NULL,
                language VARCHAR(20) DEFAULT 'python',
                code TEXT NOT NULL,
                create_user_id INTEGER NOT NULL REFERENCES users(id),
                create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                notify_template_id INTEGER REFERENCES notify_templates(id),
                assistant_id INTEGER REFERENCES assistants(id),
                ssh_server_id INTEGER REFERENCES ssh_servers(id)
            )
        """)
        connection.commit()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS script_execute_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                script_id INTEGER NOT NULL REFERENCES scripts(id),
                create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                input TEXT,
                output TEXT,
                start_time DATETIME,
                end_time DATETIME,
                state VARCHAR(20) DEFAULT 'pending',
                share_token VARCHAR(64) UNIQUE,
                is_public BOOLEAN DEFAULT 0
            )
        """)
        connection.commit()
        print("   ✓ scripts table ready")
        print("   ✓ script_execute_logs table ready")

        # ============================================================
        # WAHA_SESSIONS TABLE
        # ============================================================
        print("\n[+] WAHA sessions table...")
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
        print("   ✓ waha_sessions table ready")

        # ============================================================
        # NOTIFICATION_LOGS TABLE
        # ============================================================
        print("\n[+] Notification logs table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notification_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                task_id INTEGER REFERENCES tasks(id),
                assistant_id INTEGER REFERENCES assistants(id),
                channel VARCHAR(20) DEFAULT 'telegram',
                message TEXT,
                status VARCHAR(20) DEFAULT 'sent',
                error_message TEXT,
                create_time DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        connection.commit()
        print("   ✓ notification_logs table ready")

        # ============================================================
        # DEFAULT DATA
        # ============================================================
        print("\n[*] Adding default data...")

        # Add default languages
        cursor.execute("SELECT COUNT(*) FROM languages")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO languages (name, iso_code) VALUES ('العربية', 'ar')")
            cursor.execute("INSERT INTO languages (name, iso_code) VALUES ('English', 'en')")
            connection.commit()
            print("   + Added default languages (ar, en)")
        else:
            print("   - Languages already exist")

        # Add default assistant types
        cursor.execute("SELECT COUNT(*) FROM assistant_types")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO assistant_types (name, related_action) VALUES ('Task Manager', 'task')")
            cursor.execute("INSERT INTO assistant_types (name, related_action) VALUES ('Script Runner', 'script')")
            connection.commit()
            print("   + Added default assistant types")
        else:
            print("   - Assistant types already exist")

        # Create system settings if not exists
        cursor.execute("SELECT COUNT(*) FROM system_settings")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO system_settings (title) VALUES ('Non Real Assistant')")
            connection.commit()
            print("   + Created default system settings")
        else:
            print("   - System settings already exist")

        # ============================================================
        # SET DEFAULT VALUES FOR EXISTING USERS
        # ============================================================
        print("\n[*] Setting default values for existing users...")
        cursor.execute("UPDATE users SET telegram_notify = 1 WHERE telegram_notify IS NULL")
        cursor.execute("UPDATE users SET email_notify = 0 WHERE email_notify IS NULL")
        cursor.execute("UPDATE users SET whatsapp_notify = 0 WHERE whatsapp_notify IS NULL")
        cursor.execute("UPDATE users SET browser_notify = 1 WHERE browser_notify IS NULL")
        connection.commit()
        print("   ✓ Default notification preferences set")

        # ============================================================
        # SUMMARY
        # ============================================================
        print("\n" + "=" * 60)
        print("Migration completed successfully!")
        print("=" * 60)

        # Show table summary
        print("\nDatabase tables:")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
            count = cursor.fetchone()[0]
            print(f"   - {table[0]}: {count} rows")

        return True

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        connection.rollback()
        import traceback
        traceback.print_exc()
        return False

    finally:
        cursor.close()
        connection.close()


if __name__ == '__main__':
    db_path = get_database_path()
    success = run_migration(db_path)
    sys.exit(0 if success else 1)
