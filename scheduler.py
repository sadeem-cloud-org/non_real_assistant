"""
Background Scheduler for automatic task reminders and script execution
"""

import threading
import time
import pytz
from datetime import datetime, timedelta
from models import db, Task, User, Assistant, Script, ScriptExecuteLog, NotifyTemplate, NotificationLog
from services.telegram_bot import TelegramOTPSender
from services.script_executor import ScriptExecutor
from services.waha_service import get_waha_service


def convert_to_user_timezone(utc_time, user_timezone='Africa/Cairo'):
    """Convert UTC datetime to user's timezone"""
    if not utc_time:
        return None
    try:
        # If the datetime is naive (no timezone), assume it's UTC
        if utc_time.tzinfo is None:
            utc_time = pytz.UTC.localize(utc_time)
        # Convert to user's timezone
        user_tz = pytz.timezone(user_timezone)
        return utc_time.astimezone(user_tz)
    except Exception:
        return utc_time


def get_user_language(user):
    """Get user's language code (ar, en)"""
    if user.language:
        return user.language.iso_code if hasattr(user.language, 'iso_code') else user.language
    return 'ar'  # Default to Arabic


# Notification message templates for different languages
NOTIFICATION_MESSAGES = {
    'ar': {
        'hello': 'أهلاً',
        'i_am_assistant': 'أنا المساعد',
        'task_reminder': 'أود تنبيهك بالمهمة التي يجب إنجازها في',
        'script_executed': 'تم تنفيذ السكريبت',
        'success': 'نجح ✅',
        'failed': 'فشل ❌',
        'output': 'ناتج التشغيل',
        'good_morning': 'صباح الخير!',
        'no_tasks_today': 'لا توجد مهام لليوم. استمتع بيومك!',
        'tasks_today': 'عندك {count} مهام اليوم',
        'lets_start': 'يلا نبدأ يوم منتج!',
        'default_user': 'المستخدم',
        'personal_assistant': 'المساعد الشخصي',
        'overdue_reminder': 'تنبيه: لديك {count} مهام متأخرة',
        'due_time': 'الوقت المحدد',
        'and_more_tasks': 'و {count} مهام أخرى',
        'open_task': 'فتح المهمة'
    },
    'en': {
        'hello': 'Hello',
        'i_am_assistant': "I'm your assistant",
        'task_reminder': 'Reminder for the task due at',
        'script_executed': 'Script executed',
        'success': 'Success ✅',
        'failed': 'Failed ❌',
        'output': 'Output',
        'good_morning': 'Good morning!',
        'no_tasks_today': 'No tasks for today. Enjoy your day!',
        'tasks_today': 'You have {count} tasks today',
        'lets_start': "Let's have a productive day!",
        'default_user': 'User',
        'personal_assistant': 'Personal Assistant',
        'overdue_reminder': 'Reminder: You have {count} overdue tasks',
        'due_time': 'Due',
        'and_more_tasks': 'and {count} more tasks',
        'open_task': 'Open Task'
    }
}


def get_message(lang, key, **kwargs):
    """Get translated message"""
    messages = NOTIFICATION_MESSAGES.get(lang, NOTIFICATION_MESSAGES['ar'])
    msg = messages.get(key, NOTIFICATION_MESSAGES['ar'].get(key, key))
    if kwargs:
        msg = msg.format(**kwargs)
    return msg


class TaskScheduler:
    """Background scheduler for tasks and scripts"""

    _instance_lock = threading.Lock()  # Class-level lock for singleton
    _instance = None

    def __new__(cls, app):
        """Ensure only one instance exists (singleton pattern)"""
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, app):
        # Only initialize once
        if self._initialized:
            return
        self._initialized = True

        self.app = app
        self.running = False
        self.thread = None
        self.telegram_sender = TelegramOTPSender()
        self.script_executor = ScriptExecutor()
        self.waha_service = get_waha_service()
        self._lock = threading.Lock()
        self._last_overdue_sent = {}  # Track last overdue notification time per user

    def _safe_db_operation(self, operation, max_retries=3):
        """Execute database operation with retry on lock errors"""
        for attempt in range(max_retries):
            try:
                operation()
                return
            except Exception as e:
                error_str = str(e).lower()
                if 'database is locked' in error_str or 'locked' in error_str:
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 2  # 2s, 4s, 6s
                        print(f"⏳ Database locked, retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                        try:
                            db.session.rollback()
                        except:
                            pass
                    else:
                        print(f"❌ Database still locked after {max_retries} attempts")
                        raise
                else:
                    raise

    def start(self):
        """Start the background scheduler"""
        with self._lock:
            if self.running:
                print("⚠️  Scheduler is already running")
                return

            self.running = True
            self.thread = threading.Thread(target=self._run_loop, daemon=True)
            self.thread.start()
            print("✅ Task Scheduler started")

    def stop(self):
        """Stop the background scheduler"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        print("🛑 Task Scheduler stopped")

    def _run_loop(self):
        """Main scheduler loop"""
        last_overdue_check = 0  # Track last overdue check time (hourly)

        while self.running:
            try:
                with self.app.app_context():
                    # Check for task reminders
                    self._safe_db_operation(self._check_task_reminders)

                    # Check for scheduled assistant scripts
                    self._safe_db_operation(self._check_scheduled_assistants)

                    # Check for overdue tasks every hour
                    current_time = time.time()
                    if current_time - last_overdue_check >= 3600:  # 1 hour = 3600 seconds
                        self._safe_db_operation(self._check_overdue_tasks)
                        last_overdue_check = current_time

            except Exception as e:
                print(f"❌ Scheduler error: {e}")

            # Sleep for 1 minute
            time.sleep(60)

    def _check_task_reminders(self):
        """Check and send task reminders"""
        now = datetime.utcnow()

        # Get pending tasks (not completed, not cancelled) with time in the next 1 minute
        upcoming_tasks = Task.query.filter(
            Task.complete_time.is_(None),
            Task.cancel_time.is_(None),
            Task.notify_sent == False,
            Task.time.isnot(None),
            Task.time <= now + timedelta(minutes=1),
            Task.time > now - timedelta(minutes=5)
        ).all()

        for task in upcoming_tasks:
            # Get user
            user = User.query.get(task.create_user_id)
            if not user:
                continue

            # Check if task has an assistant
            should_notify = False
            assistant = None

            if task.assistant_id:
                assistant = Assistant.query.get(task.assistant_id)
                if assistant:
                    # Check if assistant type is for tasks (task_notify type)
                    if assistant.assistant_type and assistant.assistant_type.related_action == 'task':
                        # Notify if any notification channel is enabled on assistant
                        if assistant.telegram_notify:
                            should_notify = True
            else:
                # Task without assistant - send notification based on user preferences
                should_notify = True

            # Check if user has any notification channel available
            has_telegram = user.telegram_id and (not hasattr(user, 'telegram_notify') or user.telegram_notify)
            has_whatsapp = user.whatsapp_number and user.whatsapp_notify

            if not should_notify or (not has_telegram and not has_whatsapp):
                continue

            # Get user's language
            lang = get_user_language(user)

            # Get user display name
            user_name = user.name or user.mobile or get_message(lang, 'default_user')
            assistant_name = assistant.name if assistant else get_message(lang, 'personal_assistant')

            # Format task time in user's timezone
            local_time = convert_to_user_timezone(task.time, user.timezone or 'Africa/Cairo')
            task_time = local_time.strftime('%Y-%m-%d %H:%M') if local_time else ''

            # Prepare message based on user's language
            hello = get_message(lang, 'hello')
            i_am = get_message(lang, 'i_am_assistant')
            reminder = get_message(lang, 'task_reminder')

            # Build task link
            import os
            system_url = os.getenv('SYSTEM_URL', 'http://localhost:5000')
            task_link = f"{system_url}/tasks/{task.id}"

            # Format: Hello on one line, username on new line, assistant bold
            message = f"""{hello}
<b>{user_name}</b>، {i_am}: <b>{assistant_name}</b>

{reminder}: {task_time}

📝 <b>{task.name}</b>"""

            if task.description:
                message += f"\n📋 {task.description}"

            message += f"\n\n🔗 <a href=\"{task_link}\">فتح المهمة</a>"

            notification_sent = False

            # Send Telegram notification if enabled
            if user.telegram_notify and user.telegram_id:
                result = self.telegram_sender.send_message(
                    user.telegram_id,
                    message.strip()
                )

                # Log the notification
                notification_log = NotificationLog(
                    user_id=user.id,
                    task_id=task.id,
                    assistant_id=task.assistant_id,
                    channel='telegram',
                    message=message.strip(),
                    status='sent' if result['success'] else 'failed',
                    error_message=result.get('error') if not result['success'] else None
                )
                db.session.add(notification_log)

                if result['success']:
                    notification_sent = True
                    print(f"✅ Sent Telegram reminder for task #{task.id} to user #{user.id}")
                else:
                    print(f"❌ Failed to send Telegram reminder for task #{task.id}: {result.get('error')}")

            # Send WhatsApp notification if enabled
            if user.whatsapp_notify and user.whatsapp_number:
                whatsapp_result = None
                skip_reason = None

                # Check if WAHA is configured and working
                if not self.waha_service.is_configured():
                    skip_reason = 'WAHA not configured'
                else:
                    # Check session status before sending
                    status_check = self.waha_service.get_session_status()
                    session_status = status_check.get('status', '').upper()
                    if session_status != 'WORKING':
                        skip_reason = f'Session status: {session_status}'
                    else:
                        print(f"📱 Attempting WhatsApp notification for task #{task.id} to {user.whatsapp_number}")
                        whatsapp_result = self.waha_service.send_task_reminder(user, task, system_url)

                if skip_reason:
                    print(f"⚠️  Skipping WhatsApp for task #{task.id}: {skip_reason}")
                elif whatsapp_result:
                    # Log the WhatsApp notification
                    whatsapp_log = NotificationLog(
                        user_id=user.id,
                        task_id=task.id,
                        assistant_id=task.assistant_id,
                        channel='whatsapp',
                        message=f"Task reminder: {task.name}",
                        status='sent' if whatsapp_result['success'] else 'failed',
                        error_message=whatsapp_result.get('error') if not whatsapp_result['success'] else None
                    )
                    db.session.add(whatsapp_log)

                    if whatsapp_result['success']:
                        notification_sent = True
                        print(f"✅ Sent WhatsApp reminder for task #{task.id} to user #{user.id}")
                    else:
                        print(f"❌ Failed to send WhatsApp reminder for task #{task.id}: {whatsapp_result.get('error')}")

            if notification_sent:
                # Mark notification as sent
                task.notify_sent = True

            db.session.commit()

    def _check_scheduled_assistants(self):
        """Check and execute scheduled assistant scripts"""
        now = datetime.utcnow()

        # Get assistants that are due for execution
        due_assistants = Assistant.query.filter(
            Assistant.run_every.isnot(None),
            Assistant.next_run_time.isnot(None),
            Assistant.next_run_time <= now
        ).all()

        for assistant in due_assistants:
            # Get scripts for this assistant
            scripts = Script.query.filter_by(assistant_id=assistant.id).all()

            for script in scripts:
                try:
                    # Execute script
                    result = self.script_executor.execute(script.code)

                    # Log execution
                    log = ScriptExecuteLog(
                        script_id=script.id,
                        input=None,
                        output=result.get('output', ''),
                        start_time=result.get('start_time'),
                        end_time=result.get('end_time'),
                        state='success' if result.get('success') else 'failed'
                    )
                    db.session.add(log)

                    # Send notification if enabled
                    if assistant.telegram_notify:
                        self._send_script_notification(assistant, script, result)

                    print(f"✅ Executed script #{script.id} for assistant #{assistant.id}")

                except Exception as e:
                    # Log failed execution
                    log = ScriptExecuteLog(
                        script_id=script.id,
                        input=None,
                        output=str(e),
                        start_time=now,
                        end_time=datetime.utcnow(),
                        state='failed'
                    )
                    db.session.add(log)
                    print(f"❌ Failed to execute script #{script.id}: {e}")

            # Update next run time or clear for one-time schedules
            if assistant.run_every == 'once':
                # One-time schedule - clear the schedule after execution
                assistant.run_every = None
                assistant.next_run_time = None
            else:
                # Recurring schedule - calculate next run time
                assistant.next_run_time = self._calculate_next_run(assistant.run_every)

            db.session.commit()

    def _check_overdue_tasks(self):
        """Check and send reminders for overdue tasks (runs hourly)"""
        now = datetime.utcnow()
        current_hour = now.replace(minute=0, second=0, microsecond=0)

        # Get all overdue tasks (time passed, not completed, not cancelled)
        # Group by user to send consolidated reminders
        overdue_tasks = Task.query.filter(
            Task.complete_time.is_(None),
            Task.cancel_time.is_(None),
            Task.time.isnot(None),
            Task.time < now
        ).all()

        if not overdue_tasks:
            return

        # Group tasks by user
        tasks_by_user = {}
        for task in overdue_tasks:
            if task.create_user_id not in tasks_by_user:
                tasks_by_user[task.create_user_id] = []
            tasks_by_user[task.create_user_id].append(task)

        # Get system URL for task links
        import os
        system_url = os.getenv('SYSTEM_URL', 'http://localhost:5000')

        # Send reminder to each user with overdue tasks
        for user_id, tasks in tasks_by_user.items():
            # Check if we already sent a notification to this user this hour
            last_sent = self._last_overdue_sent.get(user_id)
            if last_sent and last_sent >= current_hour:
                print(f"⏭️  Skipping overdue reminder for user #{user_id} (already sent this hour)")
                continue

            user = User.query.get(user_id)
            if not user:
                continue

            # Check if user has any notification channel enabled
            has_telegram = user.telegram_id and (not hasattr(user, 'telegram_notify') or user.telegram_notify)
            has_whatsapp = user.whatsapp_number and user.whatsapp_notify

            if not has_telegram and not has_whatsapp:
                continue

            # Get user's language
            lang = get_user_language(user)

            # Get user display name
            user_name = user.name or user.mobile or get_message(lang, 'default_user')

            # Build message using translated strings
            overdue_msg = get_message(lang, 'overdue_reminder', count=len(tasks))
            due_time_label = get_message(lang, 'due_time')
            open_task_label = get_message(lang, 'open_task')

            message = f"⚠️ {overdue_msg}\n\n"
            for task in tasks[:10]:  # Limit to 10 tasks
                local_time = convert_to_user_timezone(task.time, user.timezone or 'Africa/Cairo')
                time_str = local_time.strftime('%Y-%m-%d %H:%M') if local_time else ''
                task_link = f"{system_url}/tasks/{task.id}"
                message += f"📝 <b>{task.name}</b>\n"
                message += f"   {due_time_label}: {time_str}\n"
                message += f"   🔗 <a href=\"{task_link}\">{open_task_label}</a>\n\n"
            if len(tasks) > 10:
                more_msg = get_message(lang, 'and_more_tasks', count=len(tasks) - 10)
                message += f"... {more_msg}"

            notification_sent = False

            # Send Telegram notification
            if has_telegram:
                result = self.telegram_sender.send_message(user.telegram_id, message.strip())

                # Log the notification
                notification_log = NotificationLog(
                    user_id=user.id,
                    channel='telegram',
                    message=message.strip(),
                    status='sent' if result['success'] else 'failed',
                    error_message=result.get('error') if not result['success'] else None
                )
                db.session.add(notification_log)

                if result['success']:
                    notification_sent = True
                    print(f"✅ Sent Telegram overdue reminder to user #{user.id} ({len(tasks)} tasks)")
                else:
                    print(f"❌ Failed to send Telegram overdue reminder to user #{user.id}: {result.get('error')}")

            # Send WhatsApp notification
            if has_whatsapp:
                whatsapp_result = None
                skip_reason = None

                # Check if WAHA is configured and working
                if not self.waha_service.is_configured():
                    skip_reason = 'WAHA not configured'
                else:
                    status_check = self.waha_service.get_session_status()
                    session_status = status_check.get('status', '').upper()
                    if session_status != 'WORKING':
                        skip_reason = f'Session status: {session_status}'
                    else:
                        # Build WhatsApp message (plain text, no HTML)
                        whatsapp_msg = f"⚠️ {get_message(lang, 'overdue_reminder', count=len(tasks))}\n\n"
                        for task in tasks[:5]:  # Limit to 5 tasks for WhatsApp
                            local_time = convert_to_user_timezone(task.time, user.timezone or 'Africa/Cairo')
                            time_str = local_time.strftime('%Y-%m-%d %H:%M') if local_time else ''
                            whatsapp_msg += f"📝 *{task.name}*\n"
                            whatsapp_msg += f"   ⏰ {time_str}\n"
                            whatsapp_msg += f"   🔗 {system_url}/tasks/{task.id}\n\n"
                        if len(tasks) > 5:
                            whatsapp_msg += f"... و {len(tasks) - 5} مهام أخرى"

                        print(f"📱 Attempting WhatsApp overdue reminder for user #{user.id}")
                        whatsapp_result = self.waha_service.send_message(user.whatsapp_number, whatsapp_msg)

                if skip_reason:
                    print(f"⚠️  Skipping WhatsApp overdue reminder for user #{user.id}: {skip_reason}")
                elif whatsapp_result:
                    # Log the WhatsApp notification
                    whatsapp_log = NotificationLog(
                        user_id=user.id,
                        channel='whatsapp',
                        message=whatsapp_msg,
                        status='sent' if whatsapp_result['success'] else 'failed',
                        error_message=whatsapp_result.get('error') if not whatsapp_result['success'] else None
                    )
                    db.session.add(whatsapp_log)

                    if whatsapp_result['success']:
                        notification_sent = True
                        print(f"✅ Sent WhatsApp overdue reminder to user #{user.id} ({len(tasks)} tasks)")
                    else:
                        print(f"❌ Failed to send WhatsApp overdue reminder to user #{user.id}: {whatsapp_result.get('error')}")

            db.session.commit()

            if notification_sent:
                # Track that we sent notification to this user
                self._last_overdue_sent[user_id] = current_hour

    def _calculate_next_run(self, run_every):
        """Calculate next run time based on run_every value"""
        now = datetime.utcnow()

        if run_every == 'minute':
            return now + timedelta(minutes=1)
        elif run_every == 'hourly':
            return now + timedelta(hours=1)
        elif run_every == 'daily':
            return now + timedelta(days=1)
        elif run_every == 'weekly':
            return now + timedelta(weeks=1)
        elif run_every == 'monthly':
            return now + timedelta(days=30)
        else:
            # Default to daily
            return now + timedelta(days=1)

    def _send_script_notification(self, assistant, script, result):
        """Send script execution notification"""
        user = User.query.get(assistant.create_user_id)
        if not user or not user.telegram_id:
            return

        # Get user's language
        lang = get_user_language(user)

        # Get user display name
        user_name = user.name or user.mobile or get_message(lang, 'default_user')
        assistant_name = assistant.name

        # Get notification template if set
        template_text = None
        if assistant.notify_template_id:
            template = NotifyTemplate.query.get(assistant.notify_template_id)
            if template:
                template_text = template.text

        # Determine status
        state = get_message(lang, 'success') if result.get('success') else get_message(lang, 'failed')
        output = result.get('output', '')[:500]

        if template_text:
            message = template_text.format(
                user_name=user_name,
                assistant_name=assistant_name,
                script_name=script.name,
                state=state,
                output=output
            )
        else:
            hello = get_message(lang, 'hello')
            i_am = get_message(lang, 'i_am_assistant')
            script_exec = get_message(lang, 'script_executed')
            output_text = get_message(lang, 'output')

            message = f"""{hello} {user_name}، {i_am}: {assistant_name}

{script_exec}: {state}

📜 <b>{script.name}</b>

{output_text}:
<code>{output}</code>"""

        result = self.telegram_sender.send_message(user.telegram_id, message.strip())

        # Log the notification
        notification_log = NotificationLog(
            user_id=user.id,
            assistant_id=assistant.id,
            channel='telegram',
            message=message.strip(),
            status='sent' if result['success'] else 'failed',
            error_message=result.get('error') if not result['success'] else None
        )
        db.session.add(notification_log)
        db.session.commit()

    def send_daily_summary(self, user_id):
        """Send daily task summary to user"""
        with self.app.app_context():
            user = User.query.get(user_id)
            if not user or not user.telegram_id:
                return

            # Get user's language
            lang = get_user_language(user)

            # Get today's tasks
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today_start + timedelta(days=1)

            pending_tasks = Task.query.filter(
                Task.create_user_id == user_id,
                Task.complete_time.is_(None),
                Task.cancel_time.is_(None),
                Task.time >= today_start,
                Task.time < today_end
            ).order_by(Task.time).all()

            good_morning = get_message(lang, 'good_morning')

            if not pending_tasks:
                no_tasks = get_message(lang, 'no_tasks_today')
                message = f"🎉 <b>{good_morning}</b>\n\n{no_tasks}"
            else:
                tasks_today = get_message(lang, 'tasks_today', count=len(pending_tasks))
                message = f"🌅 <b>{good_morning}</b>\n\n{tasks_today}:\n\n"

                for i, task in enumerate(pending_tasks, 1):
                    # Convert to user's timezone
                    local_time = convert_to_user_timezone(task.time, user.timezone or 'Africa/Cairo')
                    time_text = local_time.strftime('%H:%M') if local_time else ''

                    message += f"{i}. 📝 {task.name}"
                    if time_text:
                        message += f" ({time_text})"
                    message += "\n"

                lets_start = get_message(lang, 'lets_start')
                message += f"\n💪 {lets_start}"

            # Send message
            result = self.telegram_sender.send_message(user.telegram_id, message)

            if result['success']:
                print(f"✅ Sent daily summary to user #{user_id}")
            else:
                print(f"❌ Failed to send daily summary: {result.get('error')}")


# Global scheduler lock
_scheduler_lock = threading.Lock()

def get_scheduler(app):
    """Get or create scheduler instance (thread-safe)"""
    with _scheduler_lock:
        return TaskScheduler(app)  # Singleton pattern in __new__

def start_scheduler(app):
    """Start the scheduler (thread-safe)"""
    with _scheduler_lock:
        scheduler = TaskScheduler(app)
        scheduler.start()
        return scheduler

def stop_scheduler():
    """Stop the scheduler"""
    with _scheduler_lock:
        if TaskScheduler._instance:
            TaskScheduler._instance.stop()
            TaskScheduler._instance = None
