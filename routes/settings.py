"""Settings routes - User and System settings"""

from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from models import db, User, SystemSetting, Language

settings_bp = Blueprint('settings', __name__)


# ===== Language Switching =====

@settings_bp.route('/set-language/<lang>')
def set_language(lang):
    """Set user's preferred language"""
    # Find language by iso_code
    language = Language.query.filter_by(iso_code=lang).first()
    if language:
        session['language'] = lang

        # If user is logged in, save preference
        if 'user_id' in session:
            user = User.query.get(session['user_id'])
            if user:
                user.language_id = language.id
                db.session.commit()

    # Redirect back to previous page
    return redirect(request.referrer or url_for('dashboard.dashboard'))


# ===== User Settings Page =====

@settings_bp.route('/settings')
def user_settings():
    """User settings page"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    languages = Language.query.all()
    return render_template('settings.html', active_page='settings', languages=languages)


@settings_bp.route('/settings/system')
def system_settings():
    """System settings page (admin only)"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    return render_template('system_settings.html', active_page='system_settings')


# ===== User Settings API =====

@settings_bp.route('/api/user/profile')
def get_user_profile():
    """Get current user's profile"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify(user.to_dict())


@settings_bp.route('/api/user/profile', methods=['PUT'])
def update_user_profile():
    """Update user's profile"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json()

    # Update allowed fields
    if 'name' in data:
        user.name = data['name']
    if 'email' in data:
        user.email = data['email']
    if 'language_id' in data:
        user.language_id = data['language_id']
        # Update session language
        lang = Language.query.get(data['language_id'])
        if lang:
            session['language'] = lang.iso_code
    if 'timezone' in data:
        user.timezone = data['timezone']
    if 'browser_notify' in data:
        user.browser_notify = bool(data['browser_notify'])

    db.session.commit()

    return jsonify({
        'success': True,
        'user': user.to_dict()
    })


@settings_bp.route('/api/user/mobile', methods=['PUT'])
def update_user_mobile():
    """Update user's mobile (requires verification)"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    new_mobile = data.get('mobile', '').strip()

    if not new_mobile:
        return jsonify({'error': 'Mobile number is required'}), 400

    # Check if mobile already exists
    existing = User.query.filter_by(mobile=new_mobile).first()
    if existing and existing.id != session['user_id']:
        return jsonify({'error': 'Mobile number already in use'}), 400

    user = User.query.get(session['user_id'])
    user.mobile = new_mobile
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Mobile number updated'
    })


@settings_bp.route('/api/user/telegram', methods=['PUT'])
def update_user_telegram():
    """Update user's Telegram ID"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    new_telegram_id = data.get('telegram_id', '').strip()

    if not new_telegram_id:
        return jsonify({'error': 'Telegram ID is required'}), 400

    # Check if telegram_id already exists
    existing = User.query.filter_by(telegram_id=new_telegram_id).first()
    if existing and existing.id != session['user_id']:
        return jsonify({'error': 'Telegram ID already in use'}), 400

    user = User.query.get(session['user_id'])
    user.telegram_id = new_telegram_id
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Telegram ID updated'
    })


# ===== System Settings API =====

@settings_bp.route('/api/system/settings')
def get_system_settings():
    """Get system settings"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    settings = SystemSetting.get_settings()
    return jsonify(settings.to_dict())


@settings_bp.route('/api/system/settings', methods=['PUT'])
def update_system_settings():
    """Update system settings"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    settings = SystemSetting.get_settings()

    if 'title' in data:
        settings.title = data['title']
    if 'default_language_id' in data:
        settings.default_language_id = data['default_language_id']
    if 'otp_expiration_seconds' in data:
        settings.otp_expiration_seconds = data['otp_expiration_seconds']
    if 'telegram_bot_token' in data:
        settings.telegram_bot_token = data['telegram_bot_token']

    db.session.commit()

    return jsonify({'success': True})


# ===== Languages API =====

@settings_bp.route('/api/languages')
def get_languages():
    """Get all languages"""
    languages = Language.query.all()
    return jsonify([l.to_dict() for l in languages])
