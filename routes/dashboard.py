"""Dashboard routes"""

from flask import Blueprint, render_template, session, redirect, url_for

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/dashboard')
def dashboard():
    """Dashboard page"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    return render_template('dashboard.html', active_page='dashboard')
