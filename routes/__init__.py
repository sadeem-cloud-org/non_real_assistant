"""
Routes module for Non Real Assistant.
Contains all Flask route blueprints.
"""

from flask import Blueprint

from .auth import auth_bp
from .dashboard import dashboard_bp
from .tasks import tasks_bp
from .assistants import assistants_bp
from .scripts import scripts_bp
from .executions import executions_bp
from .api import api_bp
from .settings import settings_bp
from .share import share_bp
from .translations import translations_bp
from .admin import admin_bp


def register_blueprints(app):
    """Register all blueprints with the Flask app"""
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(assistants_bp)
    app.register_blueprint(scripts_bp)
    app.register_blueprint(executions_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(share_bp)
    app.register_blueprint(translations_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp, url_prefix='/api')


__all__ = [
    'register_blueprints',
    'auth_bp',
    'dashboard_bp',
    'tasks_bp',
    'assistants_bp',
    'scripts_bp',
    'executions_bp',
    'settings_bp',
    'share_bp',
    'translations_bp',
    'admin_bp',
    'api_bp'
]
