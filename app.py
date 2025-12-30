from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from datetime import datetime, timedelta
from config import Config
from models import db
from auth import AuthService

app = Flask(__name__)
app.config.from_object(Config)

# Initialize database
db.init_app(app)

# Initialize auth service
auth_service = AuthService()

# Create tables
with app.app_context():
    db.create_all()

# Start background scheduler for reminders
from scheduler import start_scheduler

scheduler = start_scheduler(app)


@app.route('/')
def index():
    """Main route - check if user is logged in"""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login')
def login():
    """Login page"""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')


@app.route('/api/request-otp', methods=['POST'])
def request_otp():
    """API endpoint to request OTP"""
    data = request.get_json()
    phone = data.get('phone', '').strip()

    if not phone:
        return jsonify({
            'success': False,
            'message': 'يرجى إدخال رقم الهاتف / Please enter phone number'
        }), 400

    result = auth_service.request_otp(phone)
    return jsonify(result)


@app.route('/api/verify-otp', methods=['POST'])
def verify_otp():
    """API endpoint to verify OTP"""
    data = request.get_json()
    phone = data.get('phone', '').strip()
    otp_code = data.get('otp', '').strip()

    if not phone or not otp_code:
        return jsonify({
            'success': False,
            'message': 'يرجى إدخال جميع البيانات / Please enter all fields'
        }), 400

    result = auth_service.verify_otp(phone, otp_code)

    if result['success']:
        # Create session
        session.permanent = True
        session['user_id'] = result['user']['id']
        session['phone'] = result['user']['phone']

    return jsonify(result)


@app.route('/dashboard')
def dashboard():
    """Dashboard page"""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    return render_template('dashboard.html')


@app.route('/tasks')
def tasks():
    """Tasks page"""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    return render_template('tasks.html')


@app.route('/assistants')
def assistants():
    """Assistants page"""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    return render_template('assistants.html')


@app.route('/scripts')
def scripts():
    """Scripts page"""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    return render_template('scripts.html')


@app.route('/executions')
def executions():
    """Executions page"""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    return render_template('executions.html')


@app.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    return redirect(url_for('login'))


# ===== API Endpoints =====

# Dashboard Stats
@app.route('/api/notifications/permission', methods=['POST'])
def save_notification_permission():
    """Save user's browser notification permission"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    from models import User

    data = request.get_json()
    permission = data.get('permission', 'default')

    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404

    # Store in user's extra data
    extra_data = user.get_extra_data() or {}
    extra_data['browser_notifications'] = permission
    extra_data['browser_notifications_updated_at'] = datetime.utcnow().isoformat()
    user.set_extra_data(extra_data)

    db.session.commit()

    return jsonify({
        'success': True,
        'permission': permission
    })


@app.route('/api/notifications/check', methods=['GET'])
def check_notifications():
    """Check for pending notifications"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    from models import Task

    user_id = session['user_id']
    now = datetime.utcnow()

    # Get tasks with reminders in the next minute that haven't been shown as browser notification
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

        # Check if browser notification already shown
        if extra_data.get('browser_notification_shown'):
            shown_at = extra_data.get('browser_notification_shown_at')
            if shown_at:
                try:
                    shown_time = datetime.fromisoformat(shown_at.replace('Z', '+00:00'))
                    time_since = (now - shown_time).total_seconds()
                    if time_since < 300:  # 5 minutes
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

        # Mark as shown
        extra_data['browser_notification_shown'] = True
        extra_data['browser_notification_shown_at'] = now.isoformat()
        task.set_extra_data(extra_data)

    if notifications:
        db.session.commit()

    return jsonify({
        'notifications': notifications
    })


@app.route('/api/dashboard/stats')
def dashboard_stats():
    """Get dashboard statistics"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    from models import Assistant, Task, ActionExecution

    user_id = session['user_id']

    # Count assistants
    active_assistants = Assistant.query.filter_by(
        user_id=user_id,
        is_enabled=True
    ).count()

    # Count tasks
    # Count active tasks (new + in_progress)
    pending_tasks = Task.query.filter(
        Task.user_id == user_id,
        Task.status.in_(['new', 'in_progress'])
    ).count()

    completed_today = Task.query.filter(
        Task.user_id == user_id,
        Task.status == 'completed',
        Task.completed_at >= datetime.utcnow().date()
    ).count()

    # Recent executions
    recent_executions = ActionExecution.query.filter_by(
        user_id=user_id
    ).order_by(ActionExecution.created_at.desc()).limit(5).all()

    return jsonify({
        'active_assistants': active_assistants,
        'pending_tasks': pending_tasks,
        'completed_today': completed_today,
        'recent_executions': [e.to_dict() for e in recent_executions]
    })


# Assistant Types
@app.route('/api/assistant-types')
def get_assistant_types():
    """Get all available assistant types"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    from models import AssistantType

    types = AssistantType.query.filter_by(is_active=True).all()
    return jsonify([t.to_dict() for t in types])


# Assistants CRUD
@app.route('/api/assistants')
def get_assistants():
    """Get user's assistants"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    from models import Assistant, AssistantType

    # Auto-seed assistant types if they don't exist
    if AssistantType.query.count() == 0:
        types = [
            {'name': 'task_manager', 'display_name_ar': 'مدير مهام', 'display_name_en': 'Task Manager',
             'description': 'يدير المهام اليومية ويرسل التذكيرات', 'icon': '✅'},
            {'name': 'reminder', 'display_name_ar': 'تذكيرات', 'display_name_en': 'Reminder',
             'description': 'يرسل تذكيرات بالمواعيد والمهام المهمة', 'icon': '🔔'},
            {'name': 'automation', 'display_name_ar': 'أتمتة', 'display_name_en': 'Automation',
             'description': 'ينفذ مهام أوتوماتيكية حسب الجدول', 'icon': '🤖'},
            {'name': 'data_collector', 'display_name_ar': 'جمع بيانات', 'display_name_en': 'Data Collector',
             'description': 'يجمع البيانات من مصادر مختلفة', 'icon': '📊'},
            {'name': 'custom', 'display_name_ar': 'مخصص', 'display_name_en': 'Custom',
             'description': 'مساعد مخصص حسب احتياجاتك', 'icon': '⚙️'}
        ]
        for type_data in types:
            db.session.add(AssistantType(**type_data))
        db.session.commit()
        print("✅ Auto-seeded assistant types")

    assistants = Assistant.query.filter_by(user_id=session['user_id']).all()
    return jsonify([a.to_dict() for a in assistants])


@app.route('/api/assistants', methods=['POST'])
def create_assistant():
    """Create new assistant for user"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

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


@app.route('/api/assistants/<int:assistant_id>', methods=['PUT'])
def update_assistant(assistant_id):
    """Update assistant"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

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


@app.route('/api/assistants/<int:assistant_id>', methods=['DELETE'])
def delete_assistant(assistant_id):
    """Delete assistant"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

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


# Scripts CRUD
@app.route('/api/scripts')
def get_scripts():
    """Get user's scripts"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    from models import Script

    scripts = Script.query.filter_by(user_id=session['user_id']).all()
    return jsonify([s.to_dict() for s in scripts])


@app.route('/api/scripts', methods=['POST'])
def create_script():
    """Create new script"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    from models import Script

    data = request.get_json()

    script = Script(
        user_id=session['user_id'],
        name=data.get('name'),
        description=data.get('description'),
        language=data.get('language', 'python'),
        code=data.get('code')
    )

    db.session.add(script)
    db.session.commit()

    return jsonify(script.to_dict()), 201


@app.route('/api/scripts/<int:script_id>', methods=['PUT'])
def update_script(script_id):
    """Update script"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

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

    db.session.commit()

    return jsonify(script.to_dict())


@app.route('/api/scripts/<int:script_id>', methods=['DELETE'])
def delete_script(script_id):
    """Delete script"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

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


@app.route('/api/scripts/<int:script_id>/run', methods=['POST'])
def run_script(script_id):
    """Run a script"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    from models import Script, ScriptExecution
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

    # Create execution record
    execution = ScriptExecution(
        script_id=script_id,
        user_id=session['user_id'],
        status='running'
    )
    db.session.add(execution)
    db.session.commit()

    start_time = time.time()

    try:
        # Create temp file with script code
        extension = {
            'python': '.py',
            'javascript': '.js',
            'bash': '.sh'
        }.get(script.language, '.txt')

        with tempfile.NamedTemporaryFile(mode='w', suffix=extension, delete=False) as f:
            f.write(script.code)
            temp_path = f.name

        # Execute script
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

        # Clean up
        os.unlink(temp_path)

        # Update execution record
        execution.status = 'success' if result.returncode == 0 else 'failed'
        execution.output = result.stdout
        execution.error = result.stderr
        execution.return_code = result.returncode
        execution.execution_time = time.time() - start_time
        execution.completed_at = datetime.utcnow()
        db.session.commit()

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


# Executions API
@app.route('/api/executions')
def get_executions():
    """Get all script executions for current user"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    from models import ScriptExecution

    # Get executions ordered by most recent first
    executions = ScriptExecution.query.filter_by(
        user_id=session['user_id']
    ).order_by(ScriptExecution.started_at.desc()).limit(100).all()

    return jsonify([e.to_dict() for e in executions])


@app.route('/api/executions/<int:execution_id>')
def get_execution(execution_id):
    """Get specific execution details"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    from models import ScriptExecution

    execution = ScriptExecution.query.filter_by(
        id=execution_id,
        user_id=session['user_id']
    ).first()

    if not execution:
        return jsonify({'error': 'Not found'}), 404

    return jsonify(execution.to_dict())


# Tasks CRUD
@app.route('/api/tasks')
def get_tasks():
    """Get user's tasks"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    from models import Task

    # Get query parameters
    status = request.args.get('status')
    priority = request.args.get('priority')

    query = Task.query.filter_by(user_id=session['user_id'])

    if status:
        query = query.filter_by(status=status)
    if priority:
        query = query.filter_by(priority=priority)

    tasks = query.order_by(Task.created_at.desc()).all()
    return jsonify([t.to_dict() for t in tasks])


@app.route('/api/tasks', methods=['POST'])
def create_task():
    """Create new task"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    from models import Task
    from dateutil import parser as date_parser

    data = request.get_json()

    task = Task(
        user_id=session['user_id'],
        assistant_id=data.get('assistant_id'),
        title=data.get('title'),
        description=data.get('description'),
        priority=data.get('priority', 'medium'),
        status='new'  # Always start as 'new', auto-converts to 'in_progress' when due
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


@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    """Update task"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

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
        # Only allow manual status changes to 'completed' or 'cancelled'
        # 'new' -> 'in_progress' is handled automatically by scheduler
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


@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    """Delete task"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

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


@app.route('/api/tasks/<int:task_id>/complete', methods=['POST'])
def complete_task(task_id):
    """Mark task as completed"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    from models import Task

    task = Task.query.filter_by(
        id=task_id,
        user_id=session['user_id']
    ).first()

    if not task:
        return jsonify({'error': 'Not found'}), 404

    task.mark_completed()

    return jsonify(task.to_dict())


# Actions
@app.route('/api/actions')
def get_actions():
    """Get all actions"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

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


@app.route('/api/actions/<int:action_id>/execute', methods=['POST'])
def execute_action(action_id):
    """Execute an action"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    from script_executor import ScriptExecutor

    data = request.get_json() or {}
    input_data = data.get('input_data', {})
    input_data['user_id'] = session['user_id']

    executor = ScriptExecutor()
    result = executor.execute_action(action_id, session['user_id'], input_data)

    return jsonify(result)


# Action Executions
@app.route('/api/action-executions')
def get_action_executions():
    """Get action execution history"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    from models import ActionExecution

    limit = request.args.get('limit', 50, type=int)

    executions = ActionExecution.query.filter_by(
        user_id=session['user_id']
    ).order_by(ActionExecution.created_at.desc()).limit(limit).all()

    return jsonify([e.to_dict() for e in executions])


# Scheduler test endpoints
@app.route('/api/test/daily-summary', methods=['POST'])
def test_daily_summary():
    """Test sending daily summary"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    from scheduler import get_scheduler

    scheduler = get_scheduler(app)
    scheduler.send_daily_summary(session['user_id'])

    return jsonify({'success': True, 'message': 'Daily summary sent'})


@app.route('/api/tasks/<int:task_id>/reset-reminder', methods=['POST'])
def reset_task_reminder(task_id):
    """Reset reminder status for a task (for testing)"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    from models import Task

    task = Task.query.filter_by(
        id=task_id,
        user_id=session['user_id']
    ).first()

    if not task:
        return jsonify({'error': 'Not found'}), 404

    # Reset reminder status
    extra_data = task.get_extra_data()
    extra_data['reminder_sent'] = False
    extra_data['reminder_sent_at'] = None
    task.set_extra_data(extra_data)
    db.session.commit()

    return jsonify({'success': True, 'message': 'Reminder status reset'})


# Additional routes (placeholders for Phase 2)
@app.route('/assistants')
def assistants_page():
    """Assistants management page"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return "<h1>صفحة المساعدين - قريباً</h1><a href='/dashboard'>العودة للوحة التحكم</a>"


@app.route('/tasks')
def tasks_page():
    """Tasks management page"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return "<h1>صفحة المهام - قريباً</h1><a href='/dashboard'>العودة للوحة التحكم</a>"


@app.route('/scripts')
def scripts_page():
    """Scripts editor page"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return "<h1>محرر السكريبتات - قريباً</h1><a href='/dashboard'>العودة للوحة التحكم</a>"


@app.route('/executions')
def executions_page():
    """Execution history page"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return "<h1>سجل التنفيذ - قريباً</h1><a href='/dashboard'>العودة للوحة التحكم</a>"


@app.route('/favicon.ico')
def favicon():
    """Return empty favicon to prevent 404"""
    return '', 204


@app.route('/seed/assistant-types')
def seed_assistant_types():
    """Seed assistant types into database"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    from models import AssistantType

    # Check if types already exist
    existing = AssistantType.query.count()
    if existing > 0:
        return jsonify({
            'message': f'Assistant types already exist ({existing} types)',
            'types': [t.to_dict() for t in AssistantType.query.all()]
        })

    # Create types
    types = [
        {
            'name': 'task_manager',
            'display_name_ar': 'مدير مهام',
            'display_name_en': 'Task Manager',
            'description': 'يدير المهام اليومية ويرسل التذكيرات',
            'icon': '✅'
        },
        {
            'name': 'reminder',
            'display_name_ar': 'تذكيرات',
            'display_name_en': 'Reminder',
            'description': 'يرسل تذكيرات بالمواعيد والمهام المهمة',
            'icon': '🔔'
        },
        {
            'name': 'automation',
            'display_name_ar': 'أتمتة',
            'display_name_en': 'Automation',
            'description': 'ينفذ مهام أوتوماتيكية حسب الجدول',
            'icon': '🤖'
        },
        {
            'name': 'data_collector',
            'display_name_ar': 'جمع بيانات',
            'display_name_en': 'Data Collector',
            'description': 'يجمع البيانات من مصادر مختلفة',
            'icon': '📊'
        },
        {
            'name': 'custom',
            'display_name_ar': 'مخصص',
            'display_name_en': 'Custom',
            'description': 'مساعد مخصص حسب احتياجاتك',
            'icon': '⚙️'
        }
    ]

    created_types = []
    for type_data in types:
        assistant_type = AssistantType(**type_data)
        db.session.add(assistant_type)
        created_types.append(type_data)

    db.session.commit()

    # Return created types
    all_types = AssistantType.query.all()

    return jsonify({
        'message': f'Successfully created {len(types)} assistant types',
        'types': [t.to_dict() for t in all_types]
    })


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)