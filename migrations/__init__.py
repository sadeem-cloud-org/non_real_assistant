"""
Database migrations module for Non Real Assistant.
Contains all migration scripts for database schema updates.
"""

from .migrate import run_all_migrations, migrate_database

__all__ = ['run_all_migrations', 'migrate_database']
