"""
Background Scheduler for automatic task reminders and script execution
"""

import threading
import time
from datetime import datetime, timedelta
from models import db, Task, User, Assistant, Script, ScriptExecuteLog, NotifyTemplate
from services.telegram_bot import TelegramOTPSender
from services.script_executor import ScriptExecutor


class TaskScheduler:
    """Background scheduler for tasks and scripts"""

    def __init__(self, app):
        self.app = app
        self.running = False
        self.thread = None
        self.telegram_sender = TelegramOTPSender()
        self.script_executor = ScriptExecutor()

    def start(self):
        """Start the background scheduler"""
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
        while self.running:
            try:
                with self.app.app_context():
                    # Check for task reminders
                    self._check_task_reminders()

                    # Check for scheduled assistant scripts
                    self._check_scheduled_assistants()

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

            # Check if task has an assistant with telegram_notify enabled
            should_notify = True
            if task.assistant_id:
                assistant = Assistant.query.get(task.assistant_id)
                if assistant and not assistant.telegram_notify:
                    should_notify = False

            if not should_notify or not user.telegram_id:
                continue

            # Calculate time difference
            time_diff = task.time - now
            minutes_left = int(time_diff.total_seconds() / 60)

            if minutes_left <= 0:
                time_text = "الآن"
            elif minutes_left < 60:
                time_text = f"بعد {minutes_left} دقيقة"
            else:
                hours = minutes_left // 60
                time_text = f"بعد {hours} ساعة"

            # Prepare message
            message = f"""
⏰ <b>تذكير بمهمة</b>

📝 <b>{task.name}</b>

"""

            if task.description:
                message += f"📋 {task.description}\n\n"

            if task.time:
                time_text_formatted = task.time.strftime('%Y-%m-%d %H:%M')
                message += f"📅 الموعد: {time_text_formatted}\n"

            message += f"⏱ {time_text}\n\n"
            message += "💪 حان وقت إنجاز هذه المهمة!"

            # Send notification
            result = self.telegram_sender.send_message(
                user.telegram_id,
                message.strip()
            )

            if result['success']:
                # Mark notification as sent
                task.notify_sent = True
                db.session.commit()

                print(f"✅ Sent reminder for task #{task.id} to user #{user.id}")
            else:
                print(f"❌ Failed to send reminder for task #{task.id}: {result.get('error')}")

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

            # Update next run time
            assistant.next_run_time = self._calculate_next_run(assistant.run_every)
            db.session.commit()

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

        # Get notification template if set
        template_text = None
        if assistant.notify_template_id:
            template = NotifyTemplate.query.get(assistant.notify_template_id)
            if template:
                template_text = template.text

        if result.get('success'):
            if template_text:
                message = template_text.format(
                    script_name=script.name,
                    output=result.get('output', '')[:500]
                )
            else:
                message = f"""
✅ <b>تم تنفيذ السكريبت</b>

📜 {script.name}

النتيجة:
<code>{result.get('output', '')[:500]}</code>
"""
        else:
            message = f"""
❌ <b>فشل تنفيذ السكريبت</b>

📜 {script.name}

الخطأ:
<code>{result.get('output', '')[:500]}</code>
"""

        self.telegram_sender.send_message(user.telegram_id, message.strip())

    def send_daily_summary(self, user_id):
        """Send daily task summary to user"""
        with self.app.app_context():
            user = User.query.get(user_id)
            if not user or not user.telegram_id:
                return

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

            if not pending_tasks:
                message = "🎉 <b>صباح الخير!</b>\n\nلا توجد مهام لليوم. استمتع بيومك!"
            else:
                message = f"🌅 <b>صباح الخير!</b>\n\nعندك {len(pending_tasks)} مهام اليوم:\n\n"

                for i, task in enumerate(pending_tasks, 1):
                    time_text = task.time.strftime('%H:%M') if task.time else ''

                    message += f"{i}. 📝 {task.name}"
                    if time_text:
                        message += f" ({time_text})"
                    message += "\n"

                message += "\n💪 يلا نبدأ يوم منتج!"

            # Send message
            result = self.telegram_sender.send_message(user.telegram_id, message)

            if result['success']:
                print(f"✅ Sent daily summary to user #{user_id}")
            else:
                print(f"❌ Failed to send daily summary: {result.get('error')}")


# Global scheduler instance
_scheduler = None

def get_scheduler(app):
    """Get or create scheduler instance"""
    global _scheduler
    if _scheduler is None:
        _scheduler = TaskScheduler(app)
    return _scheduler

def start_scheduler(app):
    """Start the scheduler"""
    scheduler = get_scheduler(app)
    scheduler.start()
    return scheduler

def stop_scheduler():
    """Stop the scheduler"""
    global _scheduler
    if _scheduler:
        _scheduler.stop()
        _scheduler = None
