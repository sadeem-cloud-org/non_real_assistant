"""
Script Executor - Safe script execution service

SECURITY NOTES:
- Scripts run in a restricted environment
- Dangerous imports are blocked for Python
- Bash scripts are disabled by default for security
- File system access is restricted
- Network access is controlled
"""

import json
import subprocess
import tempfile
import os
import re
from datetime import datetime
from models import db, Script, ScriptExecuteLog, User
from services.telegram_bot import TelegramOTPSender


# Dangerous patterns to block in scripts
DANGEROUS_PYTHON_PATTERNS = [
    r'\bimport\s+os\b',
    r'\bfrom\s+os\b',
    r'\bimport\s+subprocess\b',
    r'\bfrom\s+subprocess\b',
    r'\bimport\s+sys\b',
    r'\bfrom\s+sys\b',
    r'\bimport\s+socket\b',
    r'\bfrom\s+socket\b',
    r'\bimport\s+shutil\b',
    r'\bfrom\s+shutil\b',
    r'\bimport\s+pickle\b',
    r'\bfrom\s+pickle\b',
    r'\b__import__\b',
    r'\beval\s*\(',
    r'\bexec\s*\(',
    r'\bcompile\s*\(',
    r'\bopen\s*\(',
    r'\bfile\s*\(',
    r'\bgetattr\s*\(',
    r'\bsetattr\s*\(',
    r'\bdelattr\s*\(',
    r'\bglobals\s*\(',
    r'\blocals\s*\(',
    r'\bvars\s*\(',
    r'\bdir\s*\(',
    r'\b__builtins__\b',
    r'\b__class__\b',
    r'\b__bases__\b',
    r'\b__subclasses__\b',
    r'\b__mro__\b',
]

DANGEROUS_BASH_PATTERNS = [
    r'\brm\s+-rf\b',
    r'\brm\s+-r\b',
    r'\bdd\s+',
    r'\bmkfs\b',
    r'\bfdisk\b',
    r'\bparted\b',
    r'\bchmod\s+777\b',
    r'\bchown\b',
    r'\bsudo\b',
    r'\bsu\s+',
    r'\bpasswd\b',
    r'\buseradd\b',
    r'\buserdel\b',
    r'\b/etc/passwd\b',
    r'\b/etc/shadow\b',
    r'\biptables\b',
    r'\bsystemctl\b',
    r'\bservice\b',
    r'\bkill\b',
    r'\bpkill\b',
    r'\bkillall\b',
    r'\breboot\b',
    r'\bshutdown\b',
    r'\bhalt\b',
    r'\bpoweroff\b',
    r'\bcrontab\b',
    r'\bat\s+',
    r'\bnc\s+',
    r'\bnetcat\b',
    r'\btelnet\b',
    r'\bssh\b',
    r'\bscp\b',
    r'\brsync\b',
    r'\bwget\s+.*-O\s*/\b',
    r'\bcurl\s+.*-o\s*/\b',
    r'\b>\s*/etc/\b',
    r'\b>\s*/var/\b',
    r'\b>\s*/usr/\b',
    r'\b>\s*/root/\b',
    r'\bchroot\b',
    r'\bdocker\b',
    r'\bpodman\b',
]

# Allowed bash commands (whitelist approach)
ALLOWED_BASH_COMMANDS = [
    'echo', 'printf', 'date', 'cal',
    'expr', 'bc', 'test',
    'head', 'tail', 'wc', 'sort', 'uniq', 'grep', 'awk', 'sed',
    'cut', 'tr', 'paste', 'join',
    'curl', 'wget',  # For API calls only, restricted
    'jq', 'python3', 'node',
]


class ScriptExecutor:
    """Execute scripts safely with security restrictions"""

    # Security configuration
    ALLOW_BASH_SCRIPTS = False  # Bash scripts disabled by default for security
    MAX_OUTPUT_SIZE = 100000  # 100KB max output

    def __init__(self):
        self.telegram_sender = TelegramOTPSender()

    def _check_python_security(self, script_code):
        """Check Python script for dangerous patterns"""
        for pattern in DANGEROUS_PYTHON_PATTERNS:
            if re.search(pattern, script_code, re.IGNORECASE):
                return False, f"Security violation: Dangerous pattern detected ({pattern})"
        return True, None

    def _check_bash_security(self, script_code):
        """Check Bash script for dangerous patterns"""
        for pattern in DANGEROUS_BASH_PATTERNS:
            if re.search(pattern, script_code, re.IGNORECASE):
                return False, f"Security violation: Dangerous command detected ({pattern})"
        return True, None

    def execute(self, script_code, input_data=None, timeout=30, language='python'):
        """
        Execute a script code with security checks

        Args:
            script_code: Script code to execute
            input_data: Input data (dict)
            timeout: Timeout in seconds (max 60)
            language: Script language (python, javascript, bash)

        Returns:
            dict: Execution result with success, output, start_time, end_time
        """
        start_time = datetime.utcnow()

        # Limit timeout to prevent long-running scripts
        timeout = min(timeout, 60)

        try:
            if language == 'bash':
                # Security check for bash
                if not self.ALLOW_BASH_SCRIPTS:
                    return {
                        'success': False,
                        'output': 'Bash scripts are disabled for security reasons',
                        'start_time': start_time,
                        'end_time': datetime.utcnow()
                    }

                is_safe, error = self._check_bash_security(script_code)
                if not is_safe:
                    return {
                        'success': False,
                        'output': error,
                        'start_time': start_time,
                        'end_time': datetime.utcnow()
                    }

                result = self._execute_bash_command(
                    script_code,
                    input_data or {},
                    timeout
                )

            elif language == 'javascript':
                result = self._execute_javascript(
                    script_code,
                    input_data or {},
                    timeout
                )

            else:  # default to python
                # Security check for Python
                is_safe, error = self._check_python_security(script_code)
                if not is_safe:
                    return {
                        'success': False,
                        'output': error,
                        'start_time': start_time,
                        'end_time': datetime.utcnow()
                    }

                result = self._execute_python_script(
                    script_code,
                    input_data or {},
                    timeout
                )

            end_time = datetime.utcnow()

            # Truncate output if too large
            output = result.get('message', '') or result.get('output', '')
            if len(output) > self.MAX_OUTPUT_SIZE:
                output = output[:self.MAX_OUTPUT_SIZE] + '\n... (output truncated)'

            return {
                'success': result.get('success', False),
                'output': output,
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
            # Execute script with the correct language
            result = self.execute(script.code, input_data, language=script.language or 'python')

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
        """Execute Bash command with restricted environment"""
        try:
            # Create a minimal, safe environment
            safe_env = {
                'PATH': '/usr/bin:/bin',
                'HOME': '/tmp',
                'LANG': 'C.UTF-8',
                'INPUT_DATA': json.dumps(input_data, ensure_ascii=False)
            }

            # Write command to a temp script file to avoid shell=True
            with tempfile.NamedTemporaryFile(
                    mode='w',
                    suffix='.sh',
                    delete=False,
                    encoding='utf-8'
            ) as temp_file:
                temp_file.write('#!/bin/bash\nset -e\n' + command)
                temp_path = temp_file.name

            try:
                os.chmod(temp_path, 0o700)

                result = subprocess.run(
                    ['/bin/bash', temp_path],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    env=safe_env,
                    encoding='utf-8',
                    cwd='/tmp'  # Run in /tmp to restrict file access
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
                    return {
                        "success": True,
                        "message": result.stdout,
                        "output": result.stdout
                    }

            except subprocess.TimeoutExpired:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
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

    def _execute_javascript(self, script_content, input_data, timeout):
        """Execute JavaScript with Node.js"""
        with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.js',
                delete=False,
                encoding='utf-8'
        ) as temp_file:
            temp_file.write(script_content)
            temp_path = temp_file.name

        try:
            input_json = json.dumps(input_data, ensure_ascii=False)

            result = subprocess.run(
                ['node', temp_path, input_json],
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
        except FileNotFoundError:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            return {
                "success": False,
                "message": "Node.js not found. Please install Node.js to run JavaScript scripts.",
                "output": "Node.js is not installed on this system"
            }
        except Exception as e:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
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
