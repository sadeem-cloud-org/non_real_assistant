"""Settings routes - User and System settings"""

import os
import uuid
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, current_app, send_from_directory
from werkzeug.utils import secure_filename
from models import db, User, SystemSetting, Language

settings_bp = Blueprint('settings', __name__)

# Avatar upload config
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ===== Avatar File Serving =====

@settings_bp.route('/uploads/avatars/<filename>')
def serve_avatar(filename):
    """Serve avatar files"""
    upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'avatars')
    return send_from_directory(upload_dir, filename)


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


@settings_bp.route('/api/user/avatar', methods=['POST'])
def upload_avatar():
    """Upload user avatar"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404

    if 'avatar' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['avatar']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Allowed: PNG, JPG, JPEG, GIF, WEBP'}), 400

    # Check file size
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    if size > MAX_FILE_SIZE:
        return jsonify({'error': 'File too large. Maximum size is 2MB'}), 400

    # Generate unique filename
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"

    # Create upload directory if it doesn't exist
    upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'avatars')
    os.makedirs(upload_dir, exist_ok=True)

    # Delete old avatar if exists
    if user.avatar:
        old_path = os.path.join(upload_dir, user.avatar)
        if os.path.exists(old_path):
            try:
                os.remove(old_path)
            except Exception:
                pass

    # Save new avatar
    filepath = os.path.join(upload_dir, filename)
    file.save(filepath)

    # Update user
    user.avatar = filename
    db.session.commit()

    return jsonify({
        'success': True,
        'avatar': filename,
        'url': f'/uploads/avatars/{filename}'
    })


@settings_bp.route('/api/user/avatar', methods=['DELETE'])
def delete_avatar():
    """Delete user avatar"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404

    if user.avatar:
        # Delete file
        upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'avatars')
        filepath = os.path.join(upload_dir, user.avatar)
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except Exception:
                pass

        # Update user
        user.avatar = None
        db.session.commit()

    return jsonify({'success': True})


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


# ===== Email Settings API (Admin Only) =====

def require_admin(f):
    """Decorator to require admin access"""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        user = User.query.get(session['user_id'])
        if not user or not user.is_admin:
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated


@settings_bp.route('/api/system/email-settings')
@require_admin
def get_email_settings():
    """Get email/SMTP settings"""
    return jsonify({
        'smtp_host': SystemSetting.get('email_smtp_host', ''),
        'smtp_port': SystemSetting.get('email_smtp_port', 587),
        'smtp_use_tls': SystemSetting.get('email_smtp_use_tls', True),
        'smtp_user': SystemSetting.get('email_smtp_user', ''),
        # Don't return password for security
        'from_email': SystemSetting.get('email_from_address', ''),
        'from_name': SystemSetting.get('email_from_name', 'Non Real Assistant')
    })


@settings_bp.route('/api/system/email-settings', methods=['PUT'])
@require_admin
def update_email_settings():
    """Update email/SMTP settings"""
    data = request.get_json()

    if 'smtp_host' in data:
        SystemSetting.set('email_smtp_host', data['smtp_host'])
    if 'smtp_port' in data:
        SystemSetting.set('email_smtp_port', int(data['smtp_port']))
    if 'smtp_use_tls' in data:
        SystemSetting.set('email_smtp_use_tls', bool(data['smtp_use_tls']))
    if 'smtp_user' in data:
        SystemSetting.set('email_smtp_user', data['smtp_user'])
    if 'smtp_password' in data and data['smtp_password']:
        SystemSetting.set('email_smtp_password', data['smtp_password'])
    if 'from_email' in data:
        SystemSetting.set('email_from_address', data['from_email'])
    if 'from_name' in data:
        SystemSetting.set('email_from_name', data['from_name'])

    return jsonify({'success': True})


@settings_bp.route('/api/system/email-test', methods=['POST'])
@require_admin
def test_email_settings():
    """Test email settings by sending a test email"""
    import smtplib
    from email.mime.text import MIMEText

    data = request.get_json()
    test_email = data.get('test_email')

    if not test_email:
        return jsonify({'success': False, 'error': 'Test email is required'}), 400

    # Get settings from request (to test before saving)
    smtp_host = data.get('smtp_host', '')
    smtp_port = int(data.get('smtp_port', 587))
    smtp_use_tls = data.get('smtp_use_tls', True)
    smtp_user = data.get('smtp_user', '')
    smtp_password = data.get('smtp_password', '') or SystemSetting.get('email_smtp_password', '')
    from_email = data.get('from_email', '')
    from_name = data.get('from_name', 'Non Real Assistant')

    if not all([smtp_host, smtp_user, smtp_password, from_email]):
        return jsonify({'success': False, 'error': 'Missing required settings'}), 400

    try:
        # Create test message
        msg = MIMEText('هذه رسالة اختبار من Non Real Assistant\n\nThis is a test email from Non Real Assistant', 'plain', 'utf-8')
        msg['Subject'] = '✅ Test Email - Non Real Assistant'
        msg['From'] = f'{from_name} <{from_email}>'
        msg['To'] = test_email

        # Connect and send
        if smtp_use_tls:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10)

        server.login(smtp_user, smtp_password)
        server.sendmail(from_email, test_email, msg.as_string())
        server.quit()

        return jsonify({'success': True})

    except smtplib.SMTPAuthenticationError as e:
        return jsonify({'success': False, 'error': f'Authentication failed: {str(e)}'})
    except smtplib.SMTPException as e:
        return jsonify({'success': False, 'error': f'SMTP error: {str(e)}'})
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error: {str(e)}'})
