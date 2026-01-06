"""Admin routes - Admin panel for system management"""

from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from models import db, User, Language, AssistantType, SystemSetting
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


# ===== Email Settings =====

@admin_bp.route('/email-settings')
@require_admin
def email_settings_page():
    """Email settings page"""
    return render_template('admin/email_settings.html', active_page='admin')
