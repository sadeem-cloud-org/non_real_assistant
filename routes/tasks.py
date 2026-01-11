"""Tasks routes"""

import os
import uuid
from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify, current_app
from werkzeug.utils import secure_filename
from models import db, Task, TaskAttachment, User

tasks_bp = Blueprint('tasks', __name__)

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx', 'zip', 'rar'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@tasks_bp.route('/tasks')
def tasks():
    """Tasks page"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    return render_template('tasks.html', active_page='tasks')


@tasks_bp.route('/tasks/<int:task_id>')
def task_detail(task_id):
    """Task detail page (authenticated)"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    task = Task.query.get_or_404(task_id)

    # Check if user owns this task
    if task.create_user_id != session['user_id']:
        return render_template('error.html', message='غير مصرح / Unauthorized'), 403

    return render_template('task_detail.html', task=task, active_page='tasks')


@tasks_bp.route('/api/tasks/<int:task_id>/share', methods=['POST'])
def generate_share_link(task_id):
    """Generate a public share link for a task"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    task = Task.query.get_or_404(task_id)

    # Check if user owns this task
    if task.create_user_id != session['user_id']:
        return jsonify({'error': 'Unauthorized'}), 403

    # Generate share token if not exists
    if not task.share_token:
        task.generate_share_token()
        db.session.commit()

    base_url = os.getenv('SYSTEM_URL', request.host_url.rstrip('/'))
    share_url = f"{base_url}/share/task/{task.share_token}"

    return jsonify({
        'success': True,
        'share_url': share_url,
        'share_token': task.share_token
    })


@tasks_bp.route('/api/tasks/<int:task_id>/unshare', methods=['POST'])
def remove_share_link(task_id):
    """Remove public share link from a task"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    task = Task.query.get_or_404(task_id)

    # Check if user owns this task
    if task.create_user_id != session['user_id']:
        return jsonify({'error': 'Unauthorized'}), 403

    task.share_token = None
    task.is_public = False
    db.session.commit()

    return jsonify({'success': True})


@tasks_bp.route('/api/tasks/<int:task_id>/attachments', methods=['POST'])
def upload_attachment(task_id):
    """Upload an attachment to a task"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    task = Task.query.get_or_404(task_id)

    # Check if user owns this task
    if task.create_user_id != session['user_id']:
        return jsonify({'error': 'Unauthorized'}), 403

    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400

    # Check file size
    file.seek(0, 2)
    file_size = file.tell()
    file.seek(0)

    if file_size > MAX_FILE_SIZE:
        return jsonify({'error': 'File too large (max 10MB)'}), 400

    # Create uploads directory if not exists
    upload_dir = os.path.join(current_app.root_path, 'uploads', 'tasks', str(task_id))
    os.makedirs(upload_dir, exist_ok=True)

    # Generate unique filename
    original_filename = secure_filename(file.filename)
    ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
    unique_filename = f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex

    filepath = os.path.join(upload_dir, unique_filename)
    file.save(filepath)

    # Create attachment record
    attachment = TaskAttachment(
        task_id=task_id,
        filename=unique_filename,
        original_filename=original_filename,
        file_size=file_size,
        mime_type=file.content_type,
        uploaded_by=session['user_id']
    )
    db.session.add(attachment)
    db.session.commit()

    return jsonify({
        'success': True,
        'attachment': attachment.to_dict()
    })


@tasks_bp.route('/api/tasks/<int:task_id>/attachments/<int:attachment_id>', methods=['DELETE'])
def delete_attachment(task_id, attachment_id):
    """Delete an attachment from a task"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    task = Task.query.get_or_404(task_id)

    # Check if user owns this task
    if task.create_user_id != session['user_id']:
        return jsonify({'error': 'Unauthorized'}), 403

    attachment = TaskAttachment.query.get_or_404(attachment_id)

    # Check if attachment belongs to this task
    if attachment.task_id != task_id:
        return jsonify({'error': 'Attachment not found'}), 404

    # Delete file from disk
    upload_dir = os.path.join(current_app.root_path, 'uploads', 'tasks', str(task_id))
    filepath = os.path.join(upload_dir, attachment.filename)
    if os.path.exists(filepath):
        os.remove(filepath)

    # Delete record
    db.session.delete(attachment)
    db.session.commit()

    return jsonify({'success': True})


@tasks_bp.route('/uploads/tasks/<int:task_id>/<filename>')
def serve_attachment(task_id, filename):
    """Serve task attachment file"""
    from flask import send_from_directory

    # Check if user is logged in OR if task is public
    task = Task.query.get_or_404(task_id)

    is_authorized = False
    if 'user_id' in session and task.create_user_id == session['user_id']:
        is_authorized = True
    elif task.is_public:
        is_authorized = True

    if not is_authorized:
        return jsonify({'error': 'Unauthorized'}), 401

    upload_dir = os.path.join(current_app.root_path, 'uploads', 'tasks', str(task_id))
    return send_from_directory(upload_dir, filename)
