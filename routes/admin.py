"""Admin routes - Admin panel for system management"""

from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, Response
from models import db, User, Language, AssistantType, SystemSetting, WAHASession
from services.waha_service import get_waha_service, WAHAService
from functools import wraps

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def require_admin(f):
    """Decorator to require admin access"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        user = User.query.get(session['user_id'])
        if not user or not user.is_admin:
            return redirect(url_for('dashboard.dashboard'))
        return f(*args, **kwargs)
    return decorated


def require_admin_api(f):
    """Decorator for API endpoints requiring admin access"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        user = User.query.get(session['user_id'])
        if not user or not user.is_admin:
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated


# ===== Admin Panel Page =====

@admin_bp.route('/')
@require_admin
def admin_panel():
    """Admin panel main page"""
    return render_template('admin/panel.html', active_page='admin')


# ===== Assistant Types Management =====

@admin_bp.route('/assistant-types')
@require_admin
def assistant_types_page():
    """Assistant types management page"""
    return render_template('admin/assistant_types.html', active_page='admin')


@admin_bp.route('/api/assistant-types')
@require_admin_api
def get_assistant_types():
    """Get all assistant types"""
    types = AssistantType.query.all()
    return jsonify([t.to_dict() for t in types])


@admin_bp.route('/api/assistant-types', methods=['POST'])
@require_admin_api
def create_assistant_type():
    """Create a new assistant type"""
    data = request.get_json()

    name = data.get('name', '').strip()
    related_action = data.get('related_action', 'task')

    if not name:
        return jsonify({'error': 'Name is required'}), 400

    # Check if name already exists
    existing = AssistantType.query.filter_by(name=name).first()
    if existing:
        return jsonify({'error': 'Assistant type with this name already exists'}), 400

    assistant_type = AssistantType(
        name=name,
        related_action=related_action
    )
    db.session.add(assistant_type)
    db.session.commit()

    return jsonify({
        'success': True,
        'assistant_type': assistant_type.to_dict()
    }), 201


@admin_bp.route('/api/assistant-types/<int:type_id>', methods=['PUT'])
@require_admin_api
def update_assistant_type(type_id):
    """Update an assistant type"""
    assistant_type = AssistantType.query.get(type_id)
    if not assistant_type:
        return jsonify({'error': 'Assistant type not found'}), 404

    data = request.get_json()

    if 'name' in data:
        name = data['name'].strip()
        if name:
            # Check if name already exists (except for this type)
            existing = AssistantType.query.filter_by(name=name).first()
            if existing and existing.id != type_id:
                return jsonify({'error': 'Assistant type with this name already exists'}), 400
            assistant_type.name = name

    if 'related_action' in data:
        assistant_type.related_action = data['related_action']

    db.session.commit()

    return jsonify({
        'success': True,
        'assistant_type': assistant_type.to_dict()
    })


@admin_bp.route('/api/assistant-types/<int:type_id>', methods=['DELETE'])
@require_admin_api
def delete_assistant_type(type_id):
    """Delete an assistant type"""
    assistant_type = AssistantType.query.get(type_id)
    if not assistant_type:
        return jsonify({'error': 'Assistant type not found'}), 404

    # Check if there are assistants using this type
    if assistant_type.assistants:
        return jsonify({'error': 'Cannot delete: this type is used by existing assistants'}), 400

    db.session.delete(assistant_type)
    db.session.commit()

    return jsonify({'success': True})


# ===== Users Management =====

@admin_bp.route('/users')
@require_admin
def users_page():
    """Users management page"""
    return render_template('admin/users.html', active_page='admin')


@admin_bp.route('/api/users')
@require_admin_api
def get_users():
    """Get all users"""
    users = User.query.order_by(User.create_time.desc()).all()
    return jsonify([u.to_dict() for u in users])


@admin_bp.route('/api/users', methods=['POST'])
@require_admin_api
def create_user():
    """Create a new user"""
    data = request.get_json()

    mobile = data.get('mobile', '').strip()
    if not mobile:
        return jsonify({'error': 'Mobile number is required'}), 400

    # Check if mobile already exists
    existing = User.query.filter_by(mobile=mobile).first()
    if existing:
        return jsonify({'error': 'User with this mobile already exists'}), 400

    # Check telegram_id if provided
    telegram_id = data.get('telegram_id', '').strip() or None
    if telegram_id:
        existing_telegram = User.query.filter_by(telegram_id=telegram_id).first()
        if existing_telegram:
            return jsonify({'error': 'User with this Telegram ID already exists'}), 400

    # Get default language
    language = Language.query.filter_by(iso_code='ar').first()

    user = User(
        mobile=mobile,
        name=data.get('name', '').strip() or None,
        telegram_id=telegram_id,
        email=data.get('email', '').strip() or None,
        is_admin=bool(data.get('is_admin', False)),
        language_id=language.id if language else None
    )
    db.session.add(user)
    db.session.commit()

    return jsonify({
        'success': True,
        'user': user.to_dict()
    }), 201


@admin_bp.route('/api/users/<int:user_id>', methods=['PUT'])
@require_admin_api
def update_user(user_id):
    """Update a user"""
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json()

    if 'mobile' in data:
        mobile = data['mobile'].strip()
        if mobile:
            existing = User.query.filter_by(mobile=mobile).first()
            if existing and existing.id != user_id:
                return jsonify({'error': 'Mobile already in use'}), 400
            user.mobile = mobile

    if 'telegram_id' in data:
        telegram_id = data['telegram_id'].strip() or None
        if telegram_id:
            existing = User.query.filter_by(telegram_id=telegram_id).first()
            if existing and existing.id != user_id:
                return jsonify({'error': 'Telegram ID already in use'}), 400
        user.telegram_id = telegram_id

    if 'name' in data:
        user.name = data['name'].strip() or None

    if 'email' in data:
        user.email = data['email'].strip() or None

    if 'is_admin' in data:
        # Don't allow removing your own admin status
        current_user = User.query.get(session['user_id'])
        if user.id != current_user.id:
            user.is_admin = bool(data['is_admin'])

    if 'language_id' in data:
        user.language_id = data['language_id']

    if 'timezone' in data:
        user.timezone = data['timezone']

    db.session.commit()

    return jsonify({
        'success': True,
        'user': user.to_dict()
    })


@admin_bp.route('/api/users/<int:user_id>', methods=['DELETE'])
@require_admin_api
def delete_user(user_id):
    """Delete a user"""
    # Don't allow deleting yourself
    if user_id == session['user_id']:
        return jsonify({'error': 'Cannot delete your own account'}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    db.session.delete(user)
    db.session.commit()

    return jsonify({'success': True})


# ===== Notification Templates =====

@admin_bp.route('/notify-templates')
@require_admin
def notify_templates_page():
    """Notification templates management page"""
    return render_template('admin/notify_templates.html', active_page='admin')


# ===== Email Settings =====

@admin_bp.route('/email-settings')
@require_admin
def email_settings_page():
    """Email settings page"""
    return render_template('admin/email_settings.html', active_page='admin')


# ===== WAHA WhatsApp Settings =====

@admin_bp.route('/waha-settings')
@require_admin
def waha_settings_page():
    """WAHA WhatsApp settings page"""
    return render_template('admin/waha_settings.html', active_page='admin')


@admin_bp.route('/api/waha-sessions')
@require_admin_api
def get_waha_sessions():
    """Get all WAHA sessions"""
    sessions = WAHASession.query.order_by(WAHASession.create_time.desc()).all()
    return jsonify([s.to_dict() for s in sessions])


@admin_bp.route('/api/waha-sessions', methods=['POST'])
@require_admin_api
def create_waha_session():
    """Create a new WAHA session"""
    data = request.get_json()

    name = data.get('name', '').strip()
    session_name = data.get('session_name', '').strip()
    api_url = data.get('api_url', '').strip()

    if not name or not session_name or not api_url:
        return jsonify({'error': 'Name, session name, and API URL are required'}), 400

    # Check if session_name already exists
    existing = WAHASession.query.filter_by(session_name=session_name).first()
    if existing:
        return jsonify({'error': 'Session with this name already exists'}), 400

    # Remove trailing slash from API URL
    api_url = api_url.rstrip('/')

    waha_session = WAHASession(
        name=name,
        session_name=session_name,
        api_url=api_url,
        api_key=data.get('api_key', '').strip() or None,
        is_default=bool(data.get('is_default', False)),
        is_active=bool(data.get('is_active', True)),
        webhook_enabled=bool(data.get('webhook_enabled', False)),
        create_user_id=session['user_id']
    )

    # If this is set as default, unset others
    if waha_session.is_default:
        WAHASession.query.update({WAHASession.is_default: False})

    db.session.add(waha_session)
    db.session.commit()

    return jsonify({
        'success': True,
        'session': waha_session.to_dict()
    }), 201


@admin_bp.route('/api/waha-sessions/<int:session_id>', methods=['GET'])
@require_admin_api
def get_waha_session(session_id):
    """Get a specific WAHA session"""
    waha_session = WAHASession.query.get(session_id)
    if not waha_session:
        return jsonify({'error': 'Session not found'}), 404

    return jsonify(waha_session.to_dict(include_api_key=True))


@admin_bp.route('/api/waha-sessions/<int:session_id>', methods=['PUT'])
@require_admin_api
def update_waha_session(session_id):
    """Update a WAHA session"""
    waha_session = WAHASession.query.get(session_id)
    if not waha_session:
        return jsonify({'error': 'Session not found'}), 404

    data = request.get_json()

    if 'name' in data:
        waha_session.name = data['name'].strip()

    if 'session_name' in data:
        new_session_name = data['session_name'].strip()
        if new_session_name != waha_session.session_name:
            existing = WAHASession.query.filter_by(session_name=new_session_name).first()
            if existing:
                return jsonify({'error': 'Session name already in use'}), 400
            waha_session.session_name = new_session_name

    if 'api_url' in data:
        waha_session.api_url = data['api_url'].strip().rstrip('/')

    if 'api_key' in data:
        waha_session.api_key = data['api_key'].strip() or None

    if 'is_active' in data:
        waha_session.is_active = bool(data['is_active'])

    if 'webhook_enabled' in data:
        waha_session.webhook_enabled = bool(data['webhook_enabled'])

    if 'is_default' in data:
        if data['is_default']:
            # Unset all others
            WAHASession.query.update({WAHASession.is_default: False})
            waha_session.is_default = True
        else:
            waha_session.is_default = False

    db.session.commit()

    return jsonify({
        'success': True,
        'session': waha_session.to_dict()
    })


@admin_bp.route('/api/waha-sessions/<int:session_id>', methods=['DELETE'])
@require_admin_api
def delete_waha_session(session_id):
    """Delete a WAHA session"""
    waha_session = WAHASession.query.get(session_id)
    if not waha_session:
        return jsonify({'error': 'Session not found'}), 404

    db.session.delete(waha_session)
    db.session.commit()

    return jsonify({'success': True})


@admin_bp.route('/api/waha-sessions/<int:session_id>/status')
@require_admin_api
def get_waha_session_status(session_id):
    """Get WAHA session status from WAHA API"""
    waha_session = WAHASession.query.get(session_id)
    if not waha_session:
        return jsonify({'error': 'Session not found'}), 404

    service = WAHAService(waha_session)
    result = service.get_session_status(waha_session)

    return jsonify(result)


@admin_bp.route('/api/waha-sessions/<int:session_id>/start', methods=['POST'])
@require_admin_api
def start_waha_session(session_id):
    """Start a WAHA session"""
    waha_session = WAHASession.query.get(session_id)
    if not waha_session:
        return jsonify({'error': 'Session not found'}), 404

    service = WAHAService(waha_session)
    result = service.start_session(waha_session)

    return jsonify(result)


@admin_bp.route('/api/waha-sessions/<int:session_id>/stop', methods=['POST'])
@require_admin_api
def stop_waha_session(session_id):
    """Stop a WAHA session"""
    waha_session = WAHASession.query.get(session_id)
    if not waha_session:
        return jsonify({'error': 'Session not found'}), 404

    service = WAHAService(waha_session)
    result = service.stop_session(waha_session)

    return jsonify(result)


@admin_bp.route('/api/waha-sessions/<int:session_id>/logout', methods=['POST'])
@require_admin_api
def logout_waha_session(session_id):
    """Logout from a WAHA session"""
    waha_session = WAHASession.query.get(session_id)
    if not waha_session:
        return jsonify({'error': 'Session not found'}), 404

    service = WAHAService(waha_session)
    result = service.logout_session(waha_session)

    return jsonify(result)


@admin_bp.route('/api/waha-sessions/<int:session_id>/qr')
@require_admin_api
def get_waha_qr_code(session_id):
    """Get QR code for WAHA session"""
    waha_session = WAHASession.query.get(session_id)
    if not waha_session:
        return jsonify({'error': 'Session not found'}), 404

    service = WAHAService(waha_session)
    result = service.get_qr_code(waha_session)

    if result['success'] and result['qr']:
        return Response(
            result['qr'],
            mimetype=result.get('content_type', 'image/png')
        )
    else:
        return jsonify({'error': result.get('error', 'QR not available')}), 400


@admin_bp.route('/api/waha-sessions/<int:session_id>/test', methods=['POST'])
@require_admin_api
def test_waha_session(session_id):
    """Send a test message via WAHA session"""
    waha_session = WAHASession.query.get(session_id)
    if not waha_session:
        return jsonify({'error': 'Session not found'}), 404

    data = request.get_json()
    phone = data.get('phone', '').strip()
    message = data.get('message', 'Test message from Non Real Assistant')

    if not phone:
        return jsonify({'error': 'Phone number is required'}), 400

    service = WAHAService(waha_session)
    result = service.send_message(phone, message, waha_session)

    return jsonify(result)


@admin_bp.route('/api/waha-sessions/<int:session_id>/set-default', methods=['POST'])
@require_admin_api
def set_default_waha_session(session_id):
    """Set a WAHA session as default"""
    waha_session = WAHASession.query.get(session_id)
    if not waha_session:
        return jsonify({'error': 'Session not found'}), 404

    success = WAHASession.set_default(session_id)

    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Failed to set default session'}), 500


@admin_bp.route('/api/waha/has-default')
@require_admin_api
def has_default_waha_session():
    """Check if there's a default WAHA session configured"""
    default_session = WAHASession.get_default()
    return jsonify({
        'has_default': default_session is not None,
        'session': default_session.to_dict() if default_session else None
    })
