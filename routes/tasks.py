"""Tasks routes"""

from flask import Blueprint, render_template, session, redirect, url_for

tasks_bp = Blueprint('tasks', __name__)


@tasks_bp.route('/tasks')
def tasks():
    """Tasks page"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    return render_template('tasks.html', active_page='tasks')
