#!/usr/bin/env python3
"""Create script_executions table"""

import sys

sys.path.insert(0, '/mnt/user-data/outputs/non_real_assistant')

from app import app, db


def create_script_executions_table():
    """Create script_executions table"""

    with app.app_context():
        # Import after app context is ready
        from models import ScriptExecution

        # Create all tables (will only create missing ones)
        db.create_all()

        print("✅ ScriptExecution table created successfully")


if __name__ == '__main__':
    create_script_executions_table()