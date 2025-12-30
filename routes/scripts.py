"""Scripts routes"""

from flask import Blueprint, render_template, session, redirect, url_for

scripts_bp = Blueprint('scripts', __name__)


@scripts_bp.route('/scripts')
def scripts():
    """Scripts page"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    return render_template('scripts.html', active_page='scripts')
