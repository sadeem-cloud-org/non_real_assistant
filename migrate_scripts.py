#!/usr/bin/env python3
"""Add scripts table to database"""

import sys

sys.path.insert(0, '/mnt/user-data/outputs/non_real_assistant')

from app import app, db


def create_scripts_table():
    """Create scripts table"""

    with app.app_context():
        # Import after app context is ready
        from models import Script

        # Create all tables (will only create missing ones)
        db.create_all()

        print("✅ Scripts table created successfully")


if __name__ == '__main__':
    create_scripts_table()