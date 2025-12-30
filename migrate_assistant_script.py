#!/usr/bin/env python3
"""Add script_id column to assistants table"""

import sys

sys.path.insert(0, '/mnt/user-data/outputs/non_real_assistant')

from app import app, db
from sqlalchemy import text


def add_script_id_column():
    """Add script_id column to assistants"""

    with app.app_context():
        # Add column using raw SQL for SQLite
        try:
            db.session.execute(text('ALTER TABLE assistants ADD COLUMN script_id INTEGER REFERENCES scripts(id)'))
            db.session.commit()
            print("✅ Added script_id column to assistants table")
        except Exception as e:
            # Column might already exist
            error_str = str(e).lower()
            if 'duplicate column name' in error_str or 'already exists' in error_str:
                print("ℹ️ script_id column already exists")
            else:
                print(f"❌ Error: {e}")
                db.session.rollback()


if __name__ == '__main__':
    add_script_id_column()