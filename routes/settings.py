"""Settings routes - User and System settings"""

from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from models import db, User, SystemSettings

settings_bp = Blueprint('settings', __name__)


# ===== Language Switching =====

@settings_bp.route('/set-language/<lang>')
def set_language(lang):
    """Set user's preferred language"""
    if lang in ['ar', 'en']:
        session['language'] = lang

        # If user is logged in, save preference
        if 'user_id' in session:
            user = User.query.get(session['user_id'])
            if user:
                user.language = lang
                db.session.commit()

    # Redirect back to previous page
    return redirect(request.referrer or url_for('dashboard.dashboard'))


# ===== User Settings Page =====

@settings_bp.route('/settings')
def user_settings():
    """User settings page"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    return render_template('settings.html', active_page='settings')


@settings_bp.route('/settings/system')
def system_settings():
    """System settings page (admin only)"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    # TODO: Add admin check
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
    if 'language' in data and data['language'] in ['ar', 'en']:
        user.language = data['language']
        session['language'] = data['language']
    if 'timezone' in data:
        user.timezone = data['timezone']
    if 'notify_telegram' in data:
        user.notify_telegram = bool(data['notify_telegram'])
    if 'notify_email' in data:
        user.notify_email = bool(data['notify_email'])
    if 'notify_browser' in data:
        user.notify_browser = bool(data['notify_browser'])

    db.session.commit()

    return jsonify({
        'success': True,
        'user': user.to_dict()
    })


@settings_bp.route('/api/user/phone', methods=['PUT'])
def update_user_phone():
    """Update user's phone (requires OTP verification)"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    new_phone = data.get('phone', '').strip()

    if not new_phone:
        return jsonify({'error': 'Phone number is required'}), 400

    # Check if phone already exists
    existing = User.query.filter_by(phone=new_phone).first()
    if existing and existing.id != session['user_id']:
        return jsonify({'error': 'Phone number already in use'}), 400

    user = User.query.get(session['user_id'])
    user.phone = new_phone
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Phone number updated'
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
    """Get all system settings"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    # TODO: Add admin check

    settings = SystemSettings.query.all()
    result = {}
    for s in settings:
        result[s.key] = {
            'value': s.get_value(),
            'type': s.value_type,
            'description': s.description
        }

    return jsonify(result)


@settings_bp.route('/api/system/settings', methods=['PUT'])
def update_system_settings():
    """Update system settings"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    # TODO: Add admin check

    data = request.get_json()

    for key, config in data.items():
        value = config.get('value')
        value_type = config.get('type', 'string')
        description = config.get('description')

        SystemSettings.set(key, value, value_type, description)

    return jsonify({'success': True})


@settings_bp.route('/api/system/settings/email', methods=['GET'])
def get_email_settings():
    """Get email configuration"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    return jsonify({
        'smtp_host': SystemSettings.get('email_smtp_host', 'smtp.gmail.com'),
        'smtp_port': SystemSettings.get('email_smtp_port', 587),
        'smtp_user': SystemSettings.get('email_smtp_user', ''),
        'smtp_use_tls': SystemSettings.get('email_smtp_use_tls', True),
        'from_email': SystemSettings.get('email_from_address', ''),
        'from_name': SystemSettings.get('email_from_name', 'Non Real Assistant'),
        # Don't return password
    })


@settings_bp.route('/api/system/settings/email', methods=['PUT'])
def update_email_settings():
    """Update email configuration"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()

    if 'smtp_host' in data:
        SystemSettings.set('email_smtp_host', data['smtp_host'])
    if 'smtp_port' in data:
        SystemSettings.set('email_smtp_port', data['smtp_port'], 'int')
    if 'smtp_user' in data:
        SystemSettings.set('email_smtp_user', data['smtp_user'])
    if 'smtp_password' in data and data['smtp_password']:
        SystemSettings.set('email_smtp_password', data['smtp_password'])
    if 'smtp_use_tls' in data:
        SystemSettings.set('email_smtp_use_tls', data['smtp_use_tls'], 'bool')
    if 'from_email' in data:
        SystemSettings.set('email_from_address', data['from_email'])
    if 'from_name' in data:
        SystemSettings.set('email_from_name', data['from_name'])

    return jsonify({'success': True})


@settings_bp.route('/api/system/settings/email/test', methods=['POST'])
def test_email_settings():
    """Test email configuration by sending a test email"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    test_email = data.get('email')

    if not test_email:
        return jsonify({'error': 'Test email address is required'}), 400

    from services.email_service import get_email_service

    email_service = get_email_service()

    result = email_service.send_email(
        test_email,
        'Test Email - Non Real Assistant',
        """
        <html>
        <body style="font-family: Arial, sans-serif; text-align: center; padding: 40px;">
            <h1 style="color: #10b981;"> Email Configuration Works!</h1>
            <p>This is a test email from Non Real Assistant.</p>
            <p>If you received this email, your SMTP configuration is correct.</p>
        </body>
        </html>
        """
    )

    if result['success']:
        return jsonify({'success': True, 'message': 'Test email sent successfully'})
    else:
        return jsonify({'success': False, 'error': result['error']}), 400
