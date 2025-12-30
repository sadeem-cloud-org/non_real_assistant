"""Executions routes"""

from flask import Blueprint, render_template, session, redirect, url_for

executions_bp = Blueprint('executions', __name__)


@executions_bp.route('/executions')
def executions():
    """Executions page"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    return render_template('executions.html', active_page='executions')
