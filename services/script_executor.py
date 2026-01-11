"""
Script Executor - Remote script execution service via SSH

SECURITY NOTES:
- Scripts run on REMOTE servers via SSH, not locally
- Each script is associated with an SSH server configuration
- Scripts should output JSON with 'result' and 'state' keys
- The 'result' is sent to Telegram, 'state' indicates success/failure

EXPECTED SCRIPT OUTPUT FORMAT:
{
    "state": "success" | "failed",
    "result": "Message to send to Telegram",
    "data": { ... }  // Optional additional data
}
"""

import json
import io
import os
from datetime import datetime
from models import db, Script, ScriptExecuteLog, User, SSHServer
from services.telegram_bot import TelegramOTPSender

# Try to import paramiko for SSH
try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False
    print("Warning: paramiko not installed. SSH execution will not work.")


class ScriptExecutor:
    """Execute scripts safely on remote servers via SSH"""

    MAX_OUTPUT_SIZE = 100000  # 100KB max output
    DEFAULT_TIMEOUT = 60  # 60 seconds default timeout

    def __init__(self):
        self.telegram_sender = TelegramOTPSender()

    def _get_ssh_client(self, ssh_server):
        """Create SSH client connection to remote server"""
        if not PARAMIKO_AVAILABLE:
            raise Exception("paramiko library not installed. Run: pip install paramiko")

        if not ssh_server.is_active:
            raise Exception(f"SSH server '{ssh_server.name}' is not active")

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            if ssh_server.auth_type == 'key' and ssh_server.private_key:
                # Use private key authentication
                key_file = io.StringIO(ssh_server.private_key)
                private_key = paramiko.RSAKey.from_private_key(key_file)
                client.connect(
                    hostname=ssh_server.host,
                    port=ssh_server.port,
                    username=ssh_server.username,
                    pkey=private_key,
                    timeout=30
                )
            else:
                # Use password authentication
                client.connect(
                    hostname=ssh_server.host,
                    port=ssh_server.port,
                    username=ssh_server.username,
                    password=ssh_server.password,
                    timeout=30
                )
            return client
        except Exception as e:
            raise Exception(f"SSH connection failed: {str(e)}")

    def _execute_remote(self, ssh_server, script_code, input_data, timeout, language='python'):
        """Execute script on remote server via SSH"""
        client = None
        try:
            client = self._get_ssh_client(ssh_server)

            # Prepare input data as JSON
            input_json = json.dumps(input_data, ensure_ascii=False)
            # Escape single quotes for shell
            input_json_escaped = input_json.replace("'", "\\'")

            # Create the remote command based on language
            if language == 'python':
                # Create a temporary Python script on remote server
                remote_script = f'''
import sys
import json

input_data = json.loads('{input_json_escaped}')

{script_code}
'''
                command = f"python3 -c {repr(remote_script)}"

            elif language == 'bash':
                # Execute bash script directly
                command = f"export INPUT_DATA='{input_json_escaped}'; {script_code}"

            elif language == 'javascript':
                # Execute with Node.js
                remote_script = f'''
const inputData = {input_json};
{script_code}
'''
                command = f"node -e {repr(remote_script)}"

            else:
                return {
                    "success": False,
                    "output": f"Unsupported language: {language}",
                    "state": "failed",
                    "result": f"Unsupported language: {language}"
                }

            # Execute command on remote server
            stdin, stdout, stderr = client.exec_command(command, timeout=timeout)

            # Get output
            stdout_text = stdout.read().decode('utf-8', errors='replace')
            stderr_text = stderr.read().decode('utf-8', errors='replace')
            exit_code = stdout.channel.recv_exit_status()

            # Truncate if too large
            if len(stdout_text) > self.MAX_OUTPUT_SIZE:
                stdout_text = stdout_text[:self.MAX_OUTPUT_SIZE] + '\n... (output truncated)'

            # Try to parse JSON output
            try:
                output_data = json.loads(stdout_text)
                state = output_data.get('state', 'success' if exit_code == 0 else 'failed')
                result = output_data.get('result', stdout_text)
                return {
                    "success": state == 'success',
                    "output": stdout_text,
                    "state": state,
                    "result": result,
                    "data": output_data.get('data')
                }
            except json.JSONDecodeError:
                # Raw output - not JSON format
                if exit_code == 0:
                    return {
                        "success": True,
                        "output": stdout_text,
                        "state": "success",
                        "result": stdout_text
                    }
                else:
                    return {
                        "success": False,
                        "output": stderr_text or stdout_text,
                        "state": "failed",
                        "result": stderr_text or stdout_text
                    }

        except paramiko.SSHException as e:
            return {
                "success": False,
                "output": f"SSH error: {str(e)}",
                "state": "failed",
                "result": f"SSH error: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "output": f"Execution error: {str(e)}",
                "state": "failed",
                "result": f"Execution error: {str(e)}"
            }
        finally:
            if client:
                client.close()

    def execute(self, script_code, input_data=None, timeout=None, language='python', ssh_server=None):
        """
        Execute a script on remote server via SSH

        Args:
            script_code: Script code to execute
            input_data: Input data (dict)
            timeout: Timeout in seconds (max 300)
            language: Script language (python, javascript, bash)
            ssh_server: SSHServer object for remote execution

        Returns:
            dict: Execution result with success, output, state, result
        """
        start_time = datetime.utcnow()
        timeout = min(timeout or self.DEFAULT_TIMEOUT, 300)  # Max 5 minutes

        if not ssh_server:
            return {
                'success': False,
                'output': 'No SSH server configured for this script',
                'state': 'failed',
                'result': 'No SSH server configured',
                'start_time': start_time,
                'end_time': datetime.utcnow()
            }

        try:
            result = self._execute_remote(
                ssh_server,
                script_code,
                input_data or {},
                timeout,
                language
            )

            result['start_time'] = start_time
            result['end_time'] = datetime.utcnow()
            return result

        except Exception as e:
            end_time = datetime.utcnow()
            return {
                'success': False,
                'output': str(e),
                'state': 'failed',
                'result': str(e),
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
                "message": "Script not found",
                "state": "failed",
                "result": "Script not found"
            }

        if not script.ssh_server:
            return {
                "success": False,
                "message": "No SSH server configured for this script",
                "state": "failed",
                "result": "No SSH server configured"
            }

        # Create execution log
        log = ScriptExecuteLog(
            script_id=script_id,
            input=json.dumps(input_data) if input_data else None,
            state='running'
        )
        db.session.add(log)
        db.session.commit()

        try:
            # Execute script on remote server
            result = self.execute(
                script.code,
                input_data,
                language=script.language or 'python',
                ssh_server=script.ssh_server
            )

            # Update log
            log.output = result.get('output', '')
            log.start_time = result.get('start_time')
            log.end_time = result.get('end_time')
            log.state = result.get('state', 'failed')
            db.session.commit()

            return result

        except Exception as e:
            log.output = str(e)
            log.end_time = datetime.utcnow()
            log.state = 'failed'
            db.session.commit()

            return {
                "success": False,
                "message": f"Execution failed: {str(e)}",
                "state": "failed",
                "result": f"Execution failed: {str(e)}"
            }

    def send_script_result(self, user_id, script_name, result):
        """
        Send script execution result to user via Telegram

        Args:
            user_id: User ID
            script_name: Name of the script
            result: Execution result dict (should have 'state' and 'result')
        """
        try:
            user = User.query.get(user_id)
            if not user or not user.telegram_id:
                print(f"User {user_id} not found or no telegram_id")
                return False

            state = result.get('state', 'unknown')
            result_message = result.get('result', result.get('output', 'No output'))

            if state == 'success':
                emoji = '✅'
                title = f'تم تنفيذ السكريبت: {script_name}'
            else:
                emoji = '❌'
                title = f'فشل تنفيذ السكريبت: {script_name}'

            message = f"{emoji} <b>{title}</b>\n\n{result_message}"

            telegram_result = self.telegram_sender.send_message(user.telegram_id, message)

            if not telegram_result['success']:
                print(f"Failed to send result to user {user_id}: {telegram_result.get('error')}")
                return False

            return True

        except Exception as e:
            print(f"Error sending script result: {e}")
            return False

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


# Example script template for users
SCRIPT_TEMPLATE = '''
"""
Expected Script Output Format
=============================

Your script should output JSON with these keys:
- state: "success" or "failed"
- result: The message to send to Telegram
- data: (optional) Additional data

Example:
"""
import json
import sys

# Get input data (passed as first argument)
if len(sys.argv) > 1:
    input_data = json.loads(sys.argv[1])
else:
    input_data = {}

# Your script logic here
try:
    # Do something...
    result = "Task completed successfully!"

    # Output JSON result
    print(json.dumps({
        "state": "success",
        "result": result,
        "data": {"key": "value"}
    }))

except Exception as e:
    print(json.dumps({
        "state": "failed",
        "result": f"Error: {str(e)}"
    }))
'''
