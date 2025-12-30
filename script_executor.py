"""
Script Executor - تنفيذ سكريبتات الإجراءات بشكل آمن
"""

import json
import subprocess
import tempfile
import os
from datetime import datetime
from models import db, Action, ActionExecution, User
from telegram_bot import TelegramOTPSender


class ScriptExecutor:
    """تنفيذ السكريبتات بشكل آمن"""

    def __init__(self):
        self.telegram_sender = TelegramOTPSender()

    def execute_action(self, action_id, user_id, input_data=None):
        """
        تنفيذ إجراء معين

        Args:
            action_id: معرف الإجراء
            user_id: معرف المستخدم
            input_data: بيانات الإدخال (dict)

        Returns:
            dict: نتيجة التنفيذ
        """
        action = Action.query.get(action_id)

        if not action or not action.is_active:
            return {
                "success": False,
                "message": "الإجراء غير موجود أو غير نشط"
            }

        # إنشاء سجل تنفيذ
        execution = ActionExecution(
            action_id=action_id,
            user_id=user_id,
            status='pending'
        )
        execution.set_input_data(input_data or {})
        db.session.add(execution)
        db.session.commit()

        try:
            # تحديث الحالة إلى قيد التنفيذ
            execution.status = 'running'
            execution.started_at = datetime.utcnow()
            db.session.commit()

            # تنفيذ السكريبت
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
                    "message": f"نوع التنفيذ غير مدعوم: {action.execution_type}"
                }

            # حفظ النتيجة
            execution.status = 'success' if result.get('success') else 'failed'
            execution.set_output_data(result)
            execution.completed_at = datetime.utcnow()

            if execution.started_at:
                execution.execution_time = (
                        execution.completed_at - execution.started_at
                ).total_seconds()

            db.session.commit()

            # معالجة الإشعارات
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
                "message": f"فشل التنفيذ: {str(e)}"
            }

    def _execute_python_script(self, script_content, input_data, timeout):
        """
        تنفيذ سكريبت Python

        Args:
            script_content: محتوى السكريبت
            input_data: بيانات الإدخال
            timeout: المهلة الزمنية بالثواني

        Returns:
            dict: نتيجة التنفيذ
        """
        # إنشاء ملف مؤقت للسكريبت
        with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.py',
                delete=False,
                encoding='utf-8'
        ) as temp_file:
            temp_file.write(script_content)
            temp_path = temp_file.name

        try:
            # تحويل البيانات إلى JSON
            input_json = json.dumps(input_data, ensure_ascii=False)

            # تنفيذ السكريبت
            result = subprocess.run(
                ['python3', temp_path, input_json],
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding='utf-8'
            )

            # حذف الملف المؤقت
            os.unlink(temp_path)

            if result.returncode != 0:
                return {
                    "success": False,
                    "message": f"خطأ في التنفيذ: {result.stderr}"
                }

            # تحليل النتيجة
            try:
                output = json.loads(result.stdout)
                return output
            except json.JSONDecodeError:
                return {
                    "success": False,
                    "message": f"خطأ في تحليل النتيجة: {result.stdout}"
                }

        except subprocess.TimeoutExpired:
            os.unlink(temp_path)
            return {
                "success": False,
                "message": f"انتهت المهلة الزمنية ({timeout} ثانية)"
            }
        except Exception as e:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            return {
                "success": False,
                "message": f"خطأ: {str(e)}"
            }

    def _execute_bash_command(self, command, input_data, timeout):
        """
        تنفيذ أمر Bash

        Args:
            command: الأمر المراد تنفيذه
            input_data: بيانات الإدخال
            timeout: المهلة الزمنية

        Returns:
            dict: نتيجة التنفيذ
        """
        try:
            # تمرير البيانات كـ environment variable
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
                    "message": f"خطأ في التنفيذ: {result.stderr}"
                }

            # محاولة تحليل النتيجة كـ JSON
            try:
                output = json.loads(result.stdout)
                return output
            except json.JSONDecodeError:
                # إذا لم تكن JSON، نرجع النص كما هو
                return {
                    "success": True,
                    "message": result.stdout,
                    "data": {"raw_output": result.stdout}
                }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "message": f"انتهت المهلة الزمنية ({timeout} ثانية)"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"خطأ: {str(e)}"
            }

    def _send_telegram_notification(self, user_id, notification):
        """
        إرسال إشعار عبر Telegram

        Args:
            user_id: معرف المستخدم
            notification: بيانات الإشعار
        """
        try:
            user = User.query.get(user_id)
            if not user:
                print(f"User {user_id} not found")
                return

            # تكوين الرسالة
            type_emoji = {
                'info': 'ℹ️',
                'success': '✅',
                'warning': '⚠️',
                'error': '❌'
            }

            emoji = type_emoji.get(notification.get('type', 'info'), 'ℹ️')
            title = notification.get('title', 'إشعار')
            body = notification.get('body', '')

            message = f"{emoji} <b>{title}</b>\n\n{body}"

            # إرسال الرسالة
            result = self.telegram_sender.send_message(user.telegram_id, message)

            if not result['success']:
                print(f"Failed to send notification to user {user_id}: {result.get('error')}")

        except Exception as e:
            print(f"Error sending notification: {e}")