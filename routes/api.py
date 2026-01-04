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
    from models import Assistant, Task, ScriptExecuteLog, Script

    user_id = session['user_id']

    # Count assistants
    total_assistants = Assistant.query.filter_by(create_user_id=user_id).count()

    # Count pending tasks (not completed, not cancelled)
    pending_tasks = Task.query.filter(
        Task.create_user_id == user_id,
        Task.complete_time.is_(None),
        Task.cancel_time.is_(None)
    ).count()

    # Count completed today
    today = datetime.utcnow().date()
    completed_today = Task.query.filter(
        Task.create_user_id == user_id,
        Task.complete_time >= datetime(today.year, today.month, today.day)
    ).count()

    # Recent script executions
    user_scripts = Script.query.filter_by(create_user_id=user_id).all()
    script_ids = [s.id for s in user_scripts]

    recent_executions = []
    if script_ids:
        recent_executions = ScriptExecuteLog.query.filter(
            ScriptExecuteLog.script_id.in_(script_ids)
        ).order_by(ScriptExecuteLog.create_time.desc()).limit(5).all()

    return jsonify({
        'total_assistants': total_assistants,
        'pending_tasks': pending_tasks,
        'completed_today': completed_today,
        'recent_executions': [e.to_dict() for e in recent_executions]
    })


# ===== Languages =====

@api_bp.route('/languages')
def get_languages():
    """Get all languages"""
    from models import Language
    languages = Language.query.all()
    return jsonify([l.to_dict() for l in languages])


# ===== Assistant Types =====

@api_bp.route('/assistant-types')
@require_auth
def get_assistant_types():
    """Get all assistant types"""
    from models import AssistantType
    types = AssistantType.query.all()
    return jsonify([t.to_dict() for t in types])


# ===== Notify Templates =====

@api_bp.route('/notify-templates')
@require_auth
def get_notify_templates():
    """Get all notification templates"""
    from models import NotifyTemplate
    templates = NotifyTemplate.query.all()
    return jsonify([t.to_dict() for t in templates])


# ===== Assistants CRUD =====

@api_bp.route('/assistants')
@require_auth
def get_assistants():
    """Get user's assistants"""
    from models import Assistant
    assistants = Assistant.query.filter_by(create_user_id=session['user_id']).all()
    return jsonify([a.to_dict() for a in assistants])


@api_bp.route('/assistants', methods=['POST'])
@require_auth
def create_assistant():
    """Create new assistant"""
    from models import Assistant

    data = request.get_json()

    assistant = Assistant(
        name=data.get('name'),
        assistant_type_id=data.get('assistant_type_id'),
        create_user_id=session['user_id'],
        telegram_notify=data.get('telegram_notify', True),
        email_notify=data.get('email_notify', False),
        notify_template_id=data.get('notify_template_id'),
        run_every=data.get('run_every'),
        next_run_time=data.get('next_run_time')
    )

    db.session.add(assistant)
    db.session.commit()

    return jsonify(assistant.to_dict()), 201


@api_bp.route('/assistants/<int:assistant_id>', methods=['GET'])
@require_auth
def get_assistant(assistant_id):
    """Get specific assistant"""
    from models import Assistant

    assistant = Assistant.query.filter_by(
        id=assistant_id,
        create_user_id=session['user_id']
    ).first()

    if not assistant:
        return jsonify({'error': 'Not found'}), 404

    return jsonify(assistant.to_dict())


@api_bp.route('/assistants/<int:assistant_id>', methods=['PUT'])
@require_auth
def update_assistant(assistant_id):
    """Update assistant"""
    from models import Assistant

    assistant = Assistant.query.filter_by(
        id=assistant_id,
        create_user_id=session['user_id']
    ).first()

    if not assistant:
        return jsonify({'error': 'Not found'}), 404

    data = request.get_json()

    if 'name' in data:
        assistant.name = data['name']
    if 'telegram_notify' in data:
        assistant.telegram_notify = data['telegram_notify']
    if 'email_notify' in data:
        assistant.email_notify = data['email_notify']
    if 'notify_template_id' in data:
        assistant.notify_template_id = data['notify_template_id']
    if 'run_every' in data:
        assistant.run_every = data['run_every']
    if 'next_run_time' in data:
        assistant.next_run_time = data['next_run_time']

    db.session.commit()

    return jsonify(assistant.to_dict())


@api_bp.route('/assistants/<int:assistant_id>', methods=['DELETE'])
@require_auth
def delete_assistant(assistant_id):
    """Delete assistant"""
    from models import Assistant

    assistant = Assistant.query.filter_by(
        id=assistant_id,
        create_user_id=session['user_id']
    ).first()

    if not assistant:
        return jsonify({'error': 'Not found'}), 404

    db.session.delete(assistant)
    db.session.commit()

    return jsonify({'success': True})


# ===== Tasks CRUD =====

@api_bp.route('/tasks')
@require_auth
def get_tasks():
    """Get user's tasks"""
    from models import Task

    assistant_id = request.args.get('assistant_id', type=int)
    status = request.args.get('status')

    query = Task.query.filter_by(create_user_id=session['user_id'])

    if assistant_id:
        query = query.filter_by(assistant_id=assistant_id)

    tasks = query.order_by(Task.create_time.desc()).all()

    # Filter by status if provided
    if status:
        tasks = [t for t in tasks if t.get_status() == status]

    return jsonify([t.to_dict() for t in tasks])


@api_bp.route('/tasks', methods=['POST'])
@require_auth
def create_task():
    """Create new task"""
    from models import Task
    from dateutil import parser as date_parser

    data = request.get_json()

    task = Task(
        name=data.get('name'),
        create_user_id=session['user_id'],
        description=data.get('description'),
        assistant_id=data.get('assistant_id')
    )

    if data.get('time'):
        try:
            task.time = date_parser.parse(data['time'])
        except:
            pass

    db.session.add(task)
    db.session.commit()

    return jsonify(task.to_dict()), 201


@api_bp.route('/tasks/<int:task_id>', methods=['GET'])
@require_auth
def get_task(task_id):
    """Get specific task"""
    from models import Task

    task = Task.query.filter_by(
        id=task_id,
        create_user_id=session['user_id']
    ).first()

    if not task:
        return jsonify({'error': 'Not found'}), 404

    return jsonify(task.to_dict())


@api_bp.route('/tasks/<int:task_id>', methods=['PUT'])
@require_auth
def update_task(task_id):
    """Update task"""
    from models import Task
    from dateutil import parser as date_parser

    task = Task.query.filter_by(
        id=task_id,
        create_user_id=session['user_id']
    ).first()

    if not task:
        return jsonify({'error': 'Not found'}), 404

    data = request.get_json()

    if 'name' in data:
        task.name = data['name']
    if 'description' in data:
        task.description = data['description']
    if 'assistant_id' in data:
        task.assistant_id = data['assistant_id']
    if 'time' in data:
        try:
            task.time = date_parser.parse(data['time']) if data['time'] else None
        except:
            pass

    db.session.commit()

    return jsonify(task.to_dict())


@api_bp.route('/tasks/<int:task_id>', methods=['DELETE'])
@require_auth
def delete_task(task_id):
    """Delete task"""
    from models import Task

    task = Task.query.filter_by(
        id=task_id,
        create_user_id=session['user_id']
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
        create_user_id=session['user_id']
    ).first()

    if not task:
        return jsonify({'error': 'Not found'}), 404

    task.mark_completed()

    return jsonify(task.to_dict())


@api_bp.route('/tasks/<int:task_id>/cancel', methods=['POST'])
@require_auth
def cancel_task(task_id):
    """Mark task as cancelled"""
    from models import Task

    task = Task.query.filter_by(
        id=task_id,
        create_user_id=session['user_id']
    ).first()

    if not task:
        return jsonify({'error': 'Not found'}), 404

    task.mark_cancelled()

    return jsonify(task.to_dict())


# ===== Scripts CRUD =====

@api_bp.route('/scripts')
@require_auth
def get_scripts():
    """Get user's scripts"""
    from models import Script

    assistant_id = request.args.get('assistant_id', type=int)

    query = Script.query.filter_by(create_user_id=session['user_id'])

    if assistant_id:
        query = query.filter_by(assistant_id=assistant_id)

    scripts = query.order_by(Script.create_time.desc()).all()
    return jsonify([s.to_dict() for s in scripts])


@api_bp.route('/scripts', methods=['POST'])
@require_auth
def create_script():
    """Create new script"""
    from models import Script

    data = request.get_json()

    script = Script(
        name=data.get('name'),
        code=data.get('code', ''),
        create_user_id=session['user_id'],
        notify_template_id=data.get('notify_template_id'),
        assistant_id=data.get('assistant_id')
    )

    db.session.add(script)
    db.session.commit()

    return jsonify(script.to_dict()), 201


@api_bp.route('/scripts/<int:script_id>', methods=['GET'])
@require_auth
def get_script(script_id):
    """Get specific script"""
    from models import Script

    script = Script.query.filter_by(
        id=script_id,
        create_user_id=session['user_id']
    ).first()

    if not script:
        return jsonify({'error': 'Not found'}), 404

    return jsonify(script.to_dict())


@api_bp.route('/scripts/<int:script_id>', methods=['PUT'])
@require_auth
def update_script(script_id):
    """Update script"""
    from models import Script

    script = Script.query.filter_by(
        id=script_id,
        create_user_id=session['user_id']
    ).first()

    if not script:
        return jsonify({'error': 'Not found'}), 404

    data = request.get_json()

    if 'name' in data:
        script.name = data['name']
    if 'code' in data:
        script.code = data['code']
    if 'notify_template_id' in data:
        script.notify_template_id = data['notify_template_id']
    if 'assistant_id' in data:
        script.assistant_id = data['assistant_id']

    db.session.commit()

    return jsonify(script.to_dict())


@api_bp.route('/scripts/<int:script_id>', methods=['DELETE'])
@require_auth
def delete_script(script_id):
    """Delete script"""
    from models import Script

    script = Script.query.filter_by(
        id=script_id,
        create_user_id=session['user_id']
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
    from models import Script, ScriptExecuteLog, User, Assistant
    import subprocess
    import tempfile
    import os

    script = Script.query.filter_by(
        id=script_id,
        create_user_id=session['user_id']
    ).first()

    if not script:
        return jsonify({'error': 'Not found'}), 404

    data = request.get_json() or {}
    input_data = data.get('input', '')

    # Create execution log
    execution = ScriptExecuteLog(
        script_id=script_id,
        input=input_data,
        state='running',
        start_time=datetime.utcnow()
    )
    db.session.add(execution)
    db.session.commit()

    try:
        # Write script to temp file and execute
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(script.code)
            temp_path = f.name

        result = subprocess.run(
            ['python3', temp_path],
            capture_output=True,
            text=True,
            timeout=30,
            input=input_data
        )

        os.unlink(temp_path)

        execution.output = result.stdout + result.stderr
        execution.state = 'success' if result.returncode == 0 else 'failed'
        execution.end_time = datetime.utcnow()
        db.session.commit()

        # Send notifications if assistant has them enabled
        if script.assistant:
            _send_script_notifications(script, execution)

        return jsonify({
            'success': True,
            'execution_id': execution.id,
            'output': execution.output,
            'state': execution.state,
            'execution_time': execution.get_execution_time()
        })

    except subprocess.TimeoutExpired:
        execution.state = 'failed'
        execution.output = 'Script execution timeout (30s)'
        execution.end_time = datetime.utcnow()
        db.session.commit()
        return jsonify({'error': 'Script execution timeout'}), 408

    except Exception as e:
        execution.state = 'failed'
        execution.output = str(e)
        execution.end_time = datetime.utcnow()
        db.session.commit()
        return jsonify({'error': str(e)}), 500


def _send_script_notifications(script, execution):
    """Send notifications for script execution"""
    from models import User
    from services.telegram_bot import TelegramOTPSender

    assistant = script.assistant
    if not assistant:
        return

    user = User.query.get(assistant.create_user_id)
    if not user:
        return

    # Prepare message from template or default
    if assistant.notify_template:
        message = assistant.notify_template.render(
            script_name=script.name,
            output=execution.output[:500] if execution.output else '',
            state=execution.state
        )
    else:
        status_emoji = '✅' if execution.state == 'success' else '❌'
        message = f"{status_emoji} تنفيذ السكريبت: {script.name}\n"
        message += f"الحالة: {execution.state}\n"
        if execution.output:
            message += f"\nالناتج:\n{execution.output[:500]}"

    # Send Telegram notification
    if assistant.telegram_notify and user.telegram_id:
        try:
            sender = TelegramOTPSender()
            sender.send_message(user.telegram_id, message)
        except Exception as e:
            print(f"Error sending Telegram notification: {e}")

    # Send Email notification
    if assistant.email_notify and user.email:
        try:
            from services.email_service import EmailService
            email_service = EmailService()
            email_service.send_email(
                user.email,
                f"نتيجة تنفيذ السكريبت: {script.name}",
                f"<pre>{message}</pre>"
            )
        except Exception as e:
            print(f"Error sending email notification: {e}")


# ===== Executions API =====

@api_bp.route('/executions')
@require_auth
def get_executions():
    """Get script execution logs"""
    from models import ScriptExecuteLog, Script

    # Get user's scripts first
    user_scripts = Script.query.filter_by(create_user_id=session['user_id']).all()
    script_ids = [s.id for s in user_scripts]

    if not script_ids:
        return jsonify([])

    executions = ScriptExecuteLog.query.filter(
        ScriptExecuteLog.script_id.in_(script_ids)
    ).order_by(ScriptExecuteLog.create_time.desc()).limit(100).all()

    return jsonify([e.to_dict() for e in executions])


@api_bp.route('/executions/<int:execution_id>')
@require_auth
def get_execution(execution_id):
    """Get specific execution details"""
    from models import ScriptExecuteLog, Script

    execution = ScriptExecuteLog.query.get(execution_id)
    if not execution:
        return jsonify({'error': 'Not found'}), 404

    # Verify ownership
    script = Script.query.get(execution.script_id)
    if not script or script.create_user_id != session['user_id']:
        return jsonify({'error': 'Not found'}), 404

    return jsonify(execution.to_dict())


@api_bp.route('/executions/<int:execution_id>/share', methods=['POST'])
@require_auth
def create_share_link(execution_id):
    """Create a public share link for execution"""
    from models import ScriptExecuteLog, Script

    execution = ScriptExecuteLog.query.get(execution_id)
    if not execution:
        return jsonify({'error': 'Not found'}), 404

    # Verify ownership
    script = Script.query.get(execution.script_id)
    if not script or script.create_user_id != session['user_id']:
        return jsonify({'error': 'Not found'}), 404

    token = execution.generate_share_token()
    db.session.commit()

    return jsonify({
        'success': True,
        'share_token': token,
        'share_url': f'/share/execution/{token}'
    })


@api_bp.route('/executions/<int:execution_id>/share', methods=['DELETE'])
@require_auth
def remove_share_link(execution_id):
    """Remove public share link"""
    from models import ScriptExecuteLog, Script

    execution = ScriptExecuteLog.query.get(execution_id)
    if not execution:
        return jsonify({'error': 'Not found'}), 404

    # Verify ownership
    script = Script.query.get(execution.script_id)
    if not script or script.create_user_id != session['user_id']:
        return jsonify({'error': 'Not found'}), 404

    execution.share_token = None
    execution.is_public = False
    db.session.commit()

    return jsonify({'success': True})


# ===== User Profile =====

@api_bp.route('/user/profile')
@require_auth
def get_user_profile():
    """Get current user's profile"""
    from models import User

    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify(user.to_dict())


@api_bp.route('/user/profile', methods=['PUT'])
@require_auth
def update_user_profile():
    """Update user's profile"""
    from models import User

    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json()

    if 'name' in data:
        user.name = data['name']
    if 'email' in data:
        user.email = data['email']
    if 'timezone' in data:
        user.timezone = data['timezone']
    if 'language_id' in data:
        user.language_id = data['language_id']
    if 'browser_notify' in data:
        user.browser_notify = data['browser_notify']

    db.session.commit()

    return jsonify({
        'success': True,
        'user': user.to_dict()
    })
