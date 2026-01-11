"""Public share routes for tasks and execution results"""

from flask import Blueprint, render_template, jsonify, session
from models import db, ScriptExecuteLog, Script, Task

share_bp = Blueprint('share', __name__)


# ===== Task Sharing =====

@share_bp.route('/share/task/<token>')
def view_shared_task(token):
    """View a publicly shared task"""
    task = Task.query.filter_by(
        share_token=token,
        is_public=True
    ).first()

    if task:
        return render_template('share_task.html', task=task)

    return render_template('share_not_found.html'), 404


@share_bp.route('/api/share/task/<token>')
def get_shared_task_api(token):
    """API to get shared task data"""
    task = Task.query.filter_by(
        share_token=token,
        is_public=True
    ).first()

    if task:
        return jsonify({
            'type': 'task',
            'task': task.to_dict(include_attachments=True)
        })

    return jsonify({'error': 'Not found'}), 404


# ===== Script Execution Sharing =====

@share_bp.route('/share/execution/<token>')
def view_shared_execution(token):
    """View a publicly shared script execution"""
    execution = ScriptExecuteLog.query.filter_by(
        share_token=token,
        is_public=True
    ).first()

    if execution:
        return render_template('share_execution.html',
                               execution=execution.to_dict(),
                               execution_type='script')

    return render_template('share_not_found.html'), 404


@share_bp.route('/api/share/execution/<token>')
def get_shared_execution_api(token):
    """API to get shared execution data"""
    execution = ScriptExecuteLog.query.filter_by(
        share_token=token,
        is_public=True
    ).first()

    if execution:
        return jsonify({
            'type': 'script',
            'execution': execution.to_dict()
        })

    return jsonify({'error': 'Not found'}), 404
