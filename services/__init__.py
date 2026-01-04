"""
Services module for Non Real Assistant.
Contains business logic and service classes.
"""

from .auth import AuthService
from .script_executor import ScriptExecutor
from .email_service import EmailService, get_email_service

__all__ = ['AuthService', 'ScriptExecutor', 'EmailService', 'get_email_service']
