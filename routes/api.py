"""API routes"""

from flask import Blueprint, request, jsonify, session
from datetime import datetime, timedelta
from models import db

api_bp = Blueprint('api', __name__)


def require_auth(f):
    """Decorator to require authentication"""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated


# ===== Dashboard Stats =====

@api_bp.route('/dashboard/stats')
@require_auth
def dashboard_stats():
    """Get dashboard statistics"""
    from models import Assistant, Task, ActionExecution

    user_id = session['user_id']

    active_assistants = Assistant.query.filter_by(
        user_id=user_id,
        is_enabled=True
    ).count()

    pending_tasks = Task.query.filter(
        Task.user_id == user_id,
        Task.status.in_(['new', 'in_progress'])
    ).count()

    completed_today = Task.query.filter(
        Task.user_id == user_id,
        Task.status == 'completed',
        Task.completed_at >= datetime.utcnow().date()
    ).count()

    recent_executions = ActionExecution.query.filter_by(
        user_id=user_id
    ).order_by(ActionExecution.created_at.desc()).limit(5).all()

    return jsonify({
        'active_assistants': active_assistants,
        'pending_tasks': pending_tasks,
        'completed_today': completed_today,
        'recent_executions': [e.to_dict() for e in recent_executions]
    })


# ===== Notifications =====

@api_bp.route('/notifications/permission', methods=['POST'])
@require_auth
def save_notification_permission():
    """Save user's browser notification permission"""
    from models import User

    data = request.get_json()
    permission = data.get('permission', 'default')

    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404

    extra_data = user.get_extra_data() if hasattr(user, 'get_extra_data') else {}
    extra_data['browser_notifications'] = permission
    extra_data['browser_notifications_updated_at'] = datetime.utcnow().isoformat()
    if hasattr(user, 'set_extra_data'):
        user.set_extra_data(extra_data)

    db.session.commit()

    return jsonify({
        'success': True,
        'permission': permission
    })


@api_bp.route('/notifications/check')
@require_auth
def check_notifications():
    """Check for pending notifications"""
    from models import Task

    user_id = session['user_id']
    now = datetime.utcnow()

    tasks = Task.query.filter(
        Task.user_id == user_id,
        Task.status.in_(['new', 'in_progress']),
        Task.reminder_time.isnot(None),
        Task.reminder_time <= now + timedelta(minutes=1),
        Task.reminder_time > now - timedelta(seconds=30)
    ).all()

    notifications = []
    for task in tasks:
        extra_data = task.get_extra_data() or {}

        if extra_data.get('browser_notification_shown'):
            shown_at = extra_data.get('browser_notification_shown_at')
            if shown_at:
                try:
                    shown_time = datetime.fromisoformat(shown_at.replace('Z', '+00:00'))
                    time_since = (now - shown_time).total_seconds()
                    if time_since < 300:
                        continue
                except:
                    pass

        notifications.append({
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'priority': task.priority,
            'due_date': task.due_date.isoformat() if task.due_date else None,
            'reminder_time': task.reminder_time.isoformat() if task.reminder_time else None
        })

        extra_data['browser_notification_shown'] = True
        extra_data['browser_notification_shown_at'] = now.isoformat()
        task.set_extra_data(extra_data)

    if notifications:
        db.session.commit()

    return jsonify({'notifications': notifications})


# ===== Assistant Types =====

@api_bp.route('/assistant-types')
@require_auth
def get_assistant_types():
    """Get all available assistant types"""
    from models import AssistantType

    types = AssistantType.query.filter_by(is_active=True).all()
    return jsonify([t.to_dict() for t in types])


# ===== Assistants CRUD =====

@api_bp.route('/assistants')
@require_auth
def get_assistants():
    """Get user's assistants"""
    from models import Assistant, AssistantType

    if AssistantType.query.count() == 0:
        _seed_assistant_types()

    assistants = Assistant.query.filter_by(user_id=session['user_id']).all()
    return jsonify([a.to_dict() for a in assistants])


@api_bp.route('/assistants', methods=['POST'])
@require_auth
def create_assistant():
    """Create new assistant"""
    from models import Assistant

    data = request.get_json()

    assistant = Assistant(
        user_id=session['user_id'],
        assistant_type_id=data.get('assistant_type_id'),
        script_id=data.get('script_id'),
        name=data.get('name'),
        is_enabled=data.get('is_enabled', True)
    )

    if data.get('settings'):
        assistant.set_settings(data['settings'])

    db.session.add(assistant)
    db.session.commit()

    return jsonify(assistant.to_dict()), 201


@api_bp.route('/assistants/<int:assistant_id>', methods=['PUT'])
@require_auth
def update_assistant(assistant_id):
    """Update assistant"""
    from models import Assistant

    assistant = Assistant.query.filter_by(
        id=assistant_id,
        user_id=session['user_id']
    ).first()

    if not assistant:
        return jsonify({'error': 'Not found'}), 404

    data = request.get_json()

    if 'name' in data:
        assistant.name = data['name']
    if 'is_enabled' in data:
        assistant.is_enabled = data['is_enabled']
    if 'script_id' in data:
        assistant.script_id = data['script_id']
    if 'settings' in data:
        assistant.set_settings(data['settings'])

    db.session.commit()

    return jsonify(assistant.to_dict())


@api_bp.route('/assistants/<int:assistant_id>', methods=['DELETE'])
@require_auth
def delete_assistant(assistant_id):
    """Delete assistant"""
    from models import Assistant

    assistant = Assistant.query.filter_by(
        id=assistant_id,
        user_id=session['user_id']
    ).first()

    if not assistant:
        return jsonify({'error': 'Not found'}), 404

    db.session.delete(assistant)
    db.session.commit()

    return jsonify({'success': True})


# ===== Scripts CRUD =====

@api_bp.route('/scripts')
@require_auth
def get_scripts():
    """Get user's scripts"""
    from models import Script

    scripts = Script.query.filter_by(user_id=session['user_id']).all()
    return jsonify([s.to_dict() for s in scripts])


@api_bp.route('/scripts', methods=['POST'])
@require_auth
def create_script():
    """Create new script"""
    from models import Script

    data = request.get_json()

    script = Script(
        user_id=session['user_id'],
        name=data.get('name'),
        description=data.get('description'),
        language=data.get('language', 'python'),
        code=data.get('code'),
        send_output_telegram=data.get('send_output_telegram', False),
        send_output_email=data.get('send_output_email', False)
    )

    db.session.add(script)
    db.session.commit()

    return jsonify(script.to_dict()), 201


@api_bp.route('/scripts/<int:script_id>', methods=['PUT'])
@require_auth
def update_script(script_id):
    """Update script"""
    from models import Script

    script = Script.query.filter_by(
        id=script_id,
        user_id=session['user_id']
    ).first()

    if not script:
        return jsonify({'error': 'Not found'}), 404

    data = request.get_json()

    if 'name' in data:
        script.name = data['name']
    if 'description' in data:
        script.description = data['description']
    if 'language' in data:
        script.language = data['language']
    if 'code' in data:
        script.code = data['code']
    if 'send_output_telegram' in data:
        script.send_output_telegram = data['send_output_telegram']
    if 'send_output_email' in data:
        script.send_output_email = data['send_output_email']

    db.session.commit()

    return jsonify(script.to_dict())


@api_bp.route('/scripts/<int:script_id>', methods=['DELETE'])
@require_auth
def delete_script(script_id):
    """Delete script"""
    from models import Script

    script = Script.query.filter_by(
        id=script_id,
        user_id=session['user_id']
    ).first()

    if not script:
        return jsonify({'error': 'Not found'}), 404

    db.session.delete(script)
    db.session.commit()

    return jsonify({'success': True})


@api_bp.route('/scripts/<int:script_id>/run', methods=['POST'])
@require_auth
def run_script(script_id):
    """Run a script"""
    from models import Script, ScriptExecution, User
    from services.telegram_bot import TelegramOTPSender
    from services.email_service import EmailService
    import subprocess
    import tempfile
    import os
    import time

    script = Script.query.filter_by(
        id=script_id,
        user_id=session['user_id']
    ).first()

    if not script:
        return jsonify({'error': 'Not found'}), 404

    execution = ScriptExecution(
        script_id=script_id,
        user_id=session['user_id'],
        status='running'
    )
    db.session.add(execution)
    db.session.commit()

    start_time = time.time()

    try:
        extension = {
            'python': '.py',
            'javascript': '.js',
            'bash': '.sh'
        }.get(script.language, '.txt')

        with tempfile.NamedTemporaryFile(mode='w', suffix=extension, delete=False) as f:
            f.write(script.code)
            temp_path = f.name

        command = {
            'python': ['python3', temp_path],
            'javascript': ['node', temp_path],
            'bash': ['bash', temp_path]
        }.get(script.language)

        if not command:
            execution.status = 'failed'
            execution.error = 'Unsupported language'
            execution.completed_at = datetime.utcnow()
            execution.execution_time = time.time() - start_time
            db.session.commit()
            return jsonify({'error': 'Unsupported language'}), 400

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=30
        )

        os.unlink(temp_path)

        execution.status = 'success' if result.returncode == 0 else 'failed'
        execution.output = result.stdout
        execution.error = result.stderr
        execution.return_code = result.returncode
        execution.execution_time = time.time() - start_time
        execution.completed_at = datetime.utcnow()
        db.session.commit()

        # Send notifications if configured
        user = User.query.get(session['user_id'])
        _send_execution_notifications(script, execution, user)

        return jsonify({
            'success': True,
            'execution_id': execution.id,
            'output': result.stdout,
            'error': result.stderr,
            'return_code': result.returncode,
            'execution_time': execution.execution_time
        })

    except subprocess.TimeoutExpired:
        execution.status = 'timeout'
        execution.error = 'Script execution timeout (30s)'
        execution.execution_time = time.time() - start_time
        execution.completed_at = datetime.utcnow()
        db.session.commit()
        return jsonify({'error': 'Script execution timeout'}), 408
    except Exception as e:
        execution.status = 'failed'
        execution.error = str(e)
        execution.execution_time = time.time() - start_time
        execution.completed_at = datetime.utcnow()
        db.session.commit()
        return jsonify({'error': str(e)}), 500


def _send_execution_notifications(script, execution, user):
    """Send notifications for script execution results"""
    from services.telegram_bot import TelegramOTPSender
    from services.email_service import EmailService

    # Determine if we should send notifications
    send_telegram = getattr(script, 'send_output_telegram', False)
    send_email = getattr(script, 'send_output_email', False)

    if not send_telegram and not send_email:
        return

    # Prepare status emoji and text
    status_emoji = {
        'success': '✅',
        'failed': '❌',
        'timeout': '⏱️'
    }.get(execution.status, '❓')

    status_text = {
        'success': 'نجح',
        'failed': 'فشل',
        'timeout': 'انتهت المهلة'
    }.get(execution.status, execution.status)

    # Generate share link if public sharing is needed
    share_url = None
    if execution.is_public and execution.share_token:
        share_url = f"/share/execution/{execution.share_token}"

    # Send to Telegram
    if send_telegram and user and user.telegram_id and user.notify_telegram:
        try:
            telegram_sender = TelegramOTPSender()

            output_preview = execution.output[:500] if execution.output else ''
            if execution.output and len(execution.output) > 500:
                output_preview += '\n... (تم اقتطاع النتيجة)'

            error_preview = execution.error[:300] if execution.error else ''

            message = f"{status_emoji} <b>نتيجة تنفيذ السكريبت</b>\n\n"
            message += f"📝 <b>السكريبت:</b> {script.name}\n"
            message += f"📊 <b>الحالة:</b> {status_text}\n"
            message += f"⏱️ <b>وقت التنفيذ:</b> {execution.execution_time:.2f}s\n"

            if output_preview:
                message += f"\n<b>الناتج:</b>\n<pre>{output_preview}</pre>"

            if error_preview:
                message += f"\n<b>الخطأ:</b>\n<pre>{error_preview}</pre>"

            if share_url:
                message += f"\n\n🔗 <a href='{share_url}'>عرض النتيجة الكاملة</a>"

            result = telegram_sender.send_message(user.telegram_id, message)

            if result.get('success'):
                execution.telegram_sent = True
                db.session.commit()
        except Exception as e:
            print(f"Error sending Telegram notification: {e}")

    # Send to Email
    if send_email and user and user.email and user.notify_email:
        try:
            email_service = EmailService()

            result = email_service.send_execution_result(
                user=user,
                script_name=script.name,
                status=execution.status,
                output=execution.output,
                error=execution.error,
                share_url=share_url
            )

            if result.get('success'):
                execution.email_sent = True
                db.session.commit()
        except Exception as e:
            print(f"Error sending email notification: {e}")


# ===== Executions API =====

@api_bp.route('/executions')
@require_auth
def get_executions():
    """Get all script executions"""
    from models import ScriptExecution

    executions = ScriptExecution.query.filter_by(
        user_id=session['user_id']
    ).order_by(ScriptExecution.started_at.desc()).limit(100).all()

    return jsonify([e.to_dict() for e in executions])


@api_bp.route('/executions/<int:execution_id>')
@require_auth
def get_execution(execution_id):
    """Get specific execution details"""
    from models import ScriptExecution

    execution = ScriptExecution.query.filter_by(
        id=execution_id,
        user_id=session['user_id']
    ).first()

    if not execution:
        return jsonify({'error': 'Not found'}), 404

    return jsonify(execution.to_dict())


# ===== Tasks CRUD =====

@api_bp.route('/tasks')
@require_auth
def get_tasks():
    """Get user's tasks"""
    from models import Task

    status = request.args.get('status')
    priority = request.args.get('priority')

    query = Task.query.filter_by(user_id=session['user_id'])

    if status:
        query = query.filter_by(status=status)
    if priority:
        query = query.filter_by(priority=priority)

    tasks = query.order_by(Task.created_at.desc()).all()
    return jsonify([t.to_dict() for t in tasks])


@api_bp.route('/tasks', methods=['POST'])
@require_auth
def create_task():
    """Create new task"""
    from models import Task
    from dateutil import parser as date_parser

    data = request.get_json()

    task = Task(
        user_id=session['user_id'],
        assistant_id=data.get('assistant_id'),
        title=data.get('title'),
        description=data.get('description'),
        priority=data.get('priority', 'medium'),
        status='new'
    )

    if data.get('due_date'):
        try:
            task.due_date = date_parser.parse(data['due_date'])
        except:
            pass

    if data.get('reminder_time'):
        try:
            task.reminder_time = date_parser.parse(data['reminder_time'])
        except:
            pass

    if data.get('tags'):
        task.set_tags(data['tags'])

    if data.get('extra_data'):
        task.set_extra_data(data['extra_data'])

    db.session.add(task)
    db.session.commit()

    return jsonify(task.to_dict()), 201


@api_bp.route('/tasks/<int:task_id>', methods=['PUT'])
@require_auth
def update_task(task_id):
    """Update task"""
    from models import Task
    from dateutil import parser as date_parser

    task = Task.query.filter_by(
        id=task_id,
        user_id=session['user_id']
    ).first()

    if not task:
        return jsonify({'error': 'Not found'}), 404

    data = request.get_json()

    if 'title' in data:
        task.title = data['title']
    if 'description' in data:
        task.description = data['description']
    if 'priority' in data:
        task.priority = data['priority']
    if 'status' in data:
        if data['status'] in ['completed', 'cancelled']:
            task.status = data['status']
            if data['status'] == 'completed':
                task.mark_completed()

    if 'due_date' in data:
        try:
            task.due_date = date_parser.parse(data['due_date']) if data['due_date'] else None
        except:
            pass

    if 'reminder_time' in data:
        try:
            task.reminder_time = date_parser.parse(data['reminder_time']) if data['reminder_time'] else None
        except:
            pass

    if 'tags' in data:
        task.set_tags(data['tags'])

    if 'extra_data' in data:
        task.set_extra_data(data['extra_data'])

    db.session.commit()

    return jsonify(task.to_dict())


@api_bp.route('/tasks/<int:task_id>', methods=['DELETE'])
@require_auth
def delete_task(task_id):
    """Delete task"""
    from models import Task

    task = Task.query.filter_by(
        id=task_id,
        user_id=session['user_id']
    ).first()

    if not task:
        return jsonify({'error': 'Not found'}), 404

    db.session.delete(task)
    db.session.commit()

    return jsonify({'success': True})


@api_bp.route('/tasks/<int:task_id>/complete', methods=['POST'])
@require_auth
def complete_task(task_id):
    """Mark task as completed"""
    from models import Task

    task = Task.query.filter_by(
        id=task_id,
        user_id=session['user_id']
    ).first()

    if not task:
        return jsonify({'error': 'Not found'}), 404

    task.mark_completed()

    return jsonify(task.to_dict())


# ===== Actions =====

@api_bp.route('/actions')
@require_auth
def get_actions():
    """Get all actions"""
    from models import Action

    assistant_type_id = request.args.get('assistant_type_id', type=int)

    if assistant_type_id:
        actions = Action.query.filter_by(
            assistant_type_id=assistant_type_id,
            is_active=True
        ).all()
    else:
        actions = Action.query.filter_by(is_active=True).all()

    return jsonify([a.to_dict() for a in actions])


@api_bp.route('/actions/<int:action_id>/execute', methods=['POST'])
@require_auth
def execute_action(action_id):
    """Execute an action"""
    from services.script_executor import ScriptExecutor

    data = request.get_json() or {}
    input_data = data.get('input_data', {})
    input_data['user_id'] = session['user_id']

    executor = ScriptExecutor()
    result = executor.execute_action(action_id, session['user_id'], input_data)

    return jsonify(result)


# ===== Action Executions =====

@api_bp.route('/action-executions')
@require_auth
def get_action_executions():
    """Get action execution history"""
    from models import ActionExecution

    limit = request.args.get('limit', 50, type=int)

    executions = ActionExecution.query.filter_by(
        user_id=session['user_id']
    ).order_by(ActionExecution.created_at.desc()).limit(limit).all()

    return jsonify([e.to_dict() for e in executions])


# ===== Utility Functions =====

def _seed_assistant_types():
    """Seed assistant types if they don't exist"""
    from models import AssistantType

    types = [
        {'name': 'task_manager', 'display_name_ar': 'مدير مهام', 'display_name_en': 'Task Manager',
         'description': 'يدير المهام اليومية ويرسل التذكيرات', 'icon': ''},
        {'name': 'reminder', 'display_name_ar': 'تذكيرات', 'display_name_en': 'Reminder',
         'description': 'يرسل تذكيرات بالمواعيد والمهام المهمة', 'icon': ''},
        {'name': 'automation', 'display_name_ar': 'أتمتة', 'display_name_en': 'Automation',
         'description': 'ينفذ مهام أوتوماتيكية حسب الجدول', 'icon': ''},
        {'name': 'data_collector', 'display_name_ar': 'جمع بيانات', 'display_name_en': 'Data Collector',
         'description': 'يجمع البيانات من مصادر مختلفة', 'icon': ''},
        {'name': 'custom', 'display_name_ar': 'مخصص', 'display_name_en': 'Custom',
         'description': 'مساعد مخصص حسب احتياجاتك', 'icon': ''}
    ]
    for type_data in types:
        db.session.add(AssistantType(**type_data))
    db.session.commit()
    print("Auto-seeded assistant types")
