"""Assistants routes"""

from flask import Blueprint, render_template, session, redirect, url_for

assistants_bp = Blueprint('assistants', __name__)


@assistants_bp.route('/assistants')
def assistants():
    """Assistants page"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    return render_template('assistants.html', active_page='assistants')
