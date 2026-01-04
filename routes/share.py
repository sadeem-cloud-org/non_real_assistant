"""Public share routes for execution results"""

from flask import Blueprint, render_template, jsonify, request
from models import db, ScriptExecution, ActionExecution

share_bp = Blueprint('share', __name__)


@share_bp.route('/share/execution/<token>')
def view_shared_execution(token):
    """View a publicly shared script execution"""
    # Try ScriptExecution first
    execution = ScriptExecution.query.filter_by(share_token=token, is_public=True).first()

    if execution:
        return render_template('share_execution.html',
                               execution=execution.to_dict(),
                               execution_type='script')

    # Try ActionExecution
    action_execution = ActionExecution.query.filter_by(share_token=token, is_public=True).first()

    if action_execution:
        return render_template('share_execution.html',
                               execution=action_execution.to_dict(),
                               execution_type='action')

    return render_template('share_not_found.html'), 404


@share_bp.route('/api/share/execution/<token>')
def get_shared_execution_api(token):
    """API to get shared execution data"""
    # Try ScriptExecution first
    execution = ScriptExecution.query.filter_by(share_token=token, is_public=True).first()

    if execution:
        return jsonify({
            'type': 'script',
            'execution': execution.to_dict()
        })

    # Try ActionExecution
    action_execution = ActionExecution.query.filter_by(share_token=token, is_public=True).first()

    if action_execution:
        return jsonify({
            'type': 'action',
            'execution': action_execution.to_dict()
        })

    return jsonify({'error': 'Not found'}), 404


@share_bp.route('/api/executions/<int:execution_id>/share', methods=['POST'])
def create_share_link(execution_id):
    """Create a public share link for an execution"""
    from flask import session

    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    execution = ScriptExecution.query.filter_by(
        id=execution_id,
        user_id=session['user_id']
    ).first()

    if not execution:
        return jsonify({'error': 'Execution not found'}), 404

    # Generate share token
    token = execution.generate_share_token()
    db.session.commit()

    return jsonify({
        'success': True,
        'share_token': token,
        'share_url': f"/share/execution/{token}"
    })


@share_bp.route('/api/executions/<int:execution_id>/unshare', methods=['POST'])
def remove_share_link(execution_id):
    """Remove public share link from an execution"""
    from flask import session

    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    execution = ScriptExecution.query.filter_by(
        id=execution_id,
        user_id=session['user_id']
    ).first()

    if not execution:
        return jsonify({'error': 'Execution not found'}), 404

    execution.is_public = False
    execution.share_token = None
    db.session.commit()

    return jsonify({'success': True})
