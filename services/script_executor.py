"""
Script Executor - Safe script execution service
"""

import json
import subprocess
import tempfile
import os
from datetime import datetime
from models import db, Script, ScriptExecuteLog, User
from services.telegram_bot import TelegramOTPSender


class ScriptExecutor:
    """Execute scripts safely"""

    def __init__(self):
        self.telegram_sender = TelegramOTPSender()

    def execute(self, script_code, input_data=None, timeout=30):
        """
        Execute a script code

        Args:
            script_code: Python script code to execute
            input_data: Input data (dict)
            timeout: Timeout in seconds

        Returns:
            dict: Execution result with success, output, start_time, end_time
        """
        start_time = datetime.utcnow()

        try:
            result = self._execute_python_script(
                script_code,
                input_data or {},
                timeout
            )

            end_time = datetime.utcnow()

            return {
                'success': result.get('success', False),
                'output': result.get('message', '') or result.get('output', ''),
                'start_time': start_time,
                'end_time': end_time,
                'data': result.get('data')
            }

        except Exception as e:
            end_time = datetime.utcnow()
            return {
                'success': False,
                'output': str(e),
                'start_time': start_time,
                'end_time': end_time
            }

    def execute_script(self, script_id, input_data=None):
        """
        Execute a script by ID and log the execution

        Args:
            script_id: Script ID
            input_data: Input data (dict)

        Returns:
            dict: Execution result
        """
        script = Script.query.get(script_id)

        if not script:
            return {
                "success": False,
                "message": "Script not found"
            }

        # Create execution log
        log = ScriptExecuteLog(
            script_id=script_id,
            input=json.dumps(input_data) if input_data else None,
            state='pending'
        )
        db.session.add(log)
        db.session.commit()

        try:
            # Execute script
            result = self.execute(script.code, input_data)

            # Update log
            log.output = result.get('output', '')
            log.start_time = result.get('start_time')
            log.end_time = result.get('end_time')
            log.state = 'success' if result.get('success') else 'failed'
            db.session.commit()

            return result

        except Exception as e:
            log.output = str(e)
            log.end_time = datetime.utcnow()
            log.state = 'failed'
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
                    "message": f"Execution error: {result.stderr}",
                    "output": result.stderr
                }

            try:
                output = json.loads(result.stdout)
                return output
            except json.JSONDecodeError:
                # Return raw output if not JSON
                return {
                    "success": True,
                    "message": result.stdout,
                    "output": result.stdout
                }

        except subprocess.TimeoutExpired:
            os.unlink(temp_path)
            return {
                "success": False,
                "message": f"Timeout ({timeout} seconds)",
                "output": f"Script timed out after {timeout} seconds"
            }
        except Exception as e:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            return {
                "success": False,
                "message": f"Error: {str(e)}",
                "output": str(e)
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
                    "message": f"Execution error: {result.stderr}",
                    "output": result.stderr
                }

            try:
                output = json.loads(result.stdout)
                return output
            except json.JSONDecodeError:
                return {
                    "success": True,
                    "message": result.stdout,
                    "output": result.stdout
                }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "message": f"Timeout ({timeout} seconds)",
                "output": f"Command timed out after {timeout} seconds"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error: {str(e)}",
                "output": str(e)
            }

    def send_notification(self, user_id, notification):
        """Send Telegram notification"""
        try:
            user = User.query.get(user_id)
            if not user or not user.telegram_id:
                print(f"User {user_id} not found or no telegram_id")
                return False

            type_emoji = {
                'info': 'ℹ️',
                'success': '✅',
                'warning': '⚠️',
                'error': '❌'
            }

            emoji = type_emoji.get(notification.get('type', 'info'), 'ℹ️')
            title = notification.get('title', 'Notification')
            body = notification.get('body', '')

            message = f"{emoji} <b>{title}</b>\n\n{body}"

            result = self.telegram_sender.send_message(user.telegram_id, message)

            if not result['success']:
                print(f"Failed to send notification to user {user_id}: {result.get('error')}")
                return False

            return True

        except Exception as e:
            print(f"Error sending notification: {e}")
            return False
