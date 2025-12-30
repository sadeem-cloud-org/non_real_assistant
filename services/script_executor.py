"""
Script Executor - Safe script execution service
"""

import json
import subprocess
import tempfile
import os
from datetime import datetime
from models import db, Action, ActionExecution, User
from services.telegram_bot import TelegramOTPSender


class ScriptExecutor:
    """Execute scripts safely"""

    def __init__(self):
        self.telegram_sender = TelegramOTPSender()

    def execute_action(self, action_id, user_id, input_data=None):
        """
        Execute a specific action

        Args:
            action_id: Action ID
            user_id: User ID
            input_data: Input data (dict)

        Returns:
            dict: Execution result
        """
        action = Action.query.get(action_id)

        if not action or not action.is_active:
            return {
                "success": False,
                "message": "Action not found or inactive"
            }

        # Create execution record
        execution = ActionExecution(
            action_id=action_id,
            user_id=user_id,
            status='pending'
        )
        execution.set_input_data(input_data or {})
        db.session.add(execution)
        db.session.commit()

        try:
            # Update status to running
            execution.status = 'running'
            execution.started_at = datetime.utcnow()
            db.session.commit()

            # Execute script
            if action.execution_type == 'python_script':
                result = self._execute_python_script(
                    action.script_content,
                    input_data or {},
                    action.timeout
                )
            elif action.execution_type == 'bash_command':
                result = self._execute_bash_command(
                    action.script_content,
                    input_data or {},
                    action.timeout
                )
            else:
                result = {
                    "success": False,
                    "message": f"Unsupported execution type: {action.execution_type}"
                }

            # Save result
            execution.status = 'success' if result.get('success') else 'failed'
            execution.set_output_data(result)
            execution.completed_at = datetime.utcnow()

            if execution.started_at:
                execution.execution_time = (
                        execution.completed_at - execution.started_at
                ).total_seconds()

            db.session.commit()

            # Handle notifications
            notification = result.get('notification')
            if notification and notification.get('send_telegram'):
                self._send_telegram_notification(user_id, notification)

            return result

        except Exception as e:
            execution.status = 'failed'
            execution.error_message = str(e)
            execution.completed_at = datetime.utcnow()

            if execution.started_at:
                execution.execution_time = (
                        execution.completed_at - execution.started_at
                ).total_seconds()

            db.session.commit()

            return {
                "success": False,
                "message": f"Execution failed: {str(e)}"
            }

    def _execute_python_script(self, script_content, input_data, timeout):
        """Execute Python script"""
        with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.py',
                delete=False,
                encoding='utf-8'
        ) as temp_file:
            temp_file.write(script_content)
            temp_path = temp_file.name

        try:
            input_json = json.dumps(input_data, ensure_ascii=False)

            result = subprocess.run(
                ['python3', temp_path, input_json],
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding='utf-8'
            )

            os.unlink(temp_path)

            if result.returncode != 0:
                return {
                    "success": False,
                    "message": f"Execution error: {result.stderr}"
                }

            try:
                output = json.loads(result.stdout)
                return output
            except json.JSONDecodeError:
                return {
                    "success": False,
                    "message": f"Error parsing result: {result.stdout}"
                }

        except subprocess.TimeoutExpired:
            os.unlink(temp_path)
            return {
                "success": False,
                "message": f"Timeout ({timeout} seconds)"
            }
        except Exception as e:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            return {
                "success": False,
                "message": f"Error: {str(e)}"
            }

    def _execute_bash_command(self, command, input_data, timeout):
        """Execute Bash command"""
        try:
            env = os.environ.copy()
            env['INPUT_DATA'] = json.dumps(input_data, ensure_ascii=False)

            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
                encoding='utf-8'
            )

            if result.returncode != 0:
                return {
                    "success": False,
                    "message": f"Execution error: {result.stderr}"
                }

            try:
                output = json.loads(result.stdout)
                return output
            except json.JSONDecodeError:
                return {
                    "success": True,
                    "message": result.stdout,
                    "data": {"raw_output": result.stdout}
                }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "message": f"Timeout ({timeout} seconds)"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error: {str(e)}"
            }

    def _send_telegram_notification(self, user_id, notification):
        """Send Telegram notification"""
        try:
            user = User.query.get(user_id)
            if not user:
                print(f"User {user_id} not found")
                return

            type_emoji = {
                'info': 'i',
                'success': '',
                'warning': '',
                'error': ''
            }

            emoji = type_emoji.get(notification.get('type', 'info'), 'i')
            title = notification.get('title', 'Notification')
            body = notification.get('body', '')

            message = f"{emoji} <b>{title}</b>\n\n{body}"

            result = self.telegram_sender.send_message(user.telegram_id, message)

            if not result['success']:
                print(f"Failed to send notification to user {user_id}: {result.get('error')}")

        except Exception as e:
            print(f"Error sending notification: {e}")
