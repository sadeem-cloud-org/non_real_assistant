"""
Background Scheduler for automatic task reminders
"""

import threading
import time
from datetime import datetime, timedelta
from models import db, Task, User, Action, Assistant
from services.telegram_bot import TelegramOTPSender
from services.script_executor import ScriptExecutor

class TaskScheduler:
    """Background scheduler for tasks and actions"""

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

                    # Check for scheduled actions
                    self._check_scheduled_actions()

            except Exception as e:
                print(f"❌ Scheduler error: {e}")

            # Sleep for 1 minute
            time.sleep(60)


    def _auto_start_tasks(self, now):
        """Automatically start tasks when their due date arrives"""
        try:
            # Find all 'new' tasks where due_date has passed or is now
            tasks_to_start = Task.query.filter(
                Task.status == 'new',
                Task.due_date.isnot(None),
                Task.due_date <= now
            ).all()

            for task in tasks_to_start:
                task.status = 'in_progress'
                db.session.add(task)
                print(f"[Scheduler] Auto-started task #{task.id}: {task.title}")

            if tasks_to_start:
                db.session.commit()
                print(f"[Scheduler] Auto-started {len(tasks_to_start)} tasks")

        except Exception as e:
            print(f"[Scheduler] Error auto-starting tasks: {str(e)}")
            db.session.rollback()

    def _check_task_reminders(self):
        """Check and send task reminders"""
        now = datetime.utcnow()

        # Auto-start tasks: Convert 'new' tasks to 'in_progress' when due_date arrives
        self._auto_start_tasks(now)

        # Get tasks with reminder_time in the next 1 minute (narrower window)
        # This prevents sending same reminder multiple times
        upcoming_tasks = Task.query.filter(
            Task.status.in_(['new', 'in_progress']),  # Check both new and in_progress
            Task.reminder_time.isnot(None),
            Task.reminder_time <= now + timedelta(minutes=1),
            Task.reminder_time > now - timedelta(seconds=30)  # Only recent ones
        ).all()

        for task in upcoming_tasks:
            # Check if we already sent reminder (avoid duplicates)
            extra_data = task.get_extra_data()

            # If reminder was sent in the last 5 minutes, skip
            if extra_data.get('reminder_sent'):
                reminder_sent_at = extra_data.get('reminder_sent_at')
                if reminder_sent_at:
                    try:
                        sent_time = datetime.fromisoformat(reminder_sent_at.replace('Z', '+00:00'))
                        time_since_sent = (now - sent_time).total_seconds()
                        if time_since_sent < 300:  # 5 minutes
                            continue
                    except:
                        pass

            # Get user
            user = User.query.get(task.user_id)
            if not user:
                continue

            # Calculate time difference
            time_diff = task.reminder_time - now
            minutes_left = int(time_diff.total_seconds() / 60)

            if minutes_left < 0:
                time_text = "الآن"
            elif minutes_left == 0:
                time_text = "الآن"
            elif minutes_left < 60:
                time_text = f"بعد {minutes_left} دقيقة"
            else:
                hours = minutes_left // 60
                time_text = f"بعد {hours} ساعة"

            # Prepare message
            priority_emoji = {
                'high': '🔴',
                'medium': '🟡',
                'low': '🟢'
            }

            emoji = priority_emoji.get(task.priority, '📝')

            message = f"""
⏰ <b>تذكير بمهمة</b>

{emoji} <b>{task.title}</b>

"""

            if task.description:
                message += f"📋 {task.description}\n\n"

            if task.due_date:
                due_text = task.due_date.strftime('%Y-%m-%d %H:%M')
                message += f"📅 موعد الاستحقاق: {due_text}\n"

            message += f"⏱ {time_text}\n\n"
            message += "💪 حان وقت إنجاز هذه المهمة!"

            # Send notification
            result = self.telegram_sender.send_message(
                user.telegram_id,
                message.strip()
            )

            if result['success']:
                # Mark reminder as sent with timestamp
                extra_data['reminder_sent'] = True
                extra_data['reminder_sent_at'] = now.isoformat()
                task.set_extra_data(extra_data)
                db.session.commit()

                print(f"✅ Sent reminder for task #{task.id} to user #{user.id}")
            else:
                print(f"❌ Failed to send reminder for task #{task.id}: {result.get('error')}")

    def _check_scheduled_actions(self):
        """Check and execute scheduled actions"""
        # This will be implemented when we add cron support
        # For now, we can execute actions based on time
        pass

    def send_daily_summary(self, user_id):
        """Send daily task summary to user"""
        with self.app.app_context():
            user = User.query.get(user_id)
            if not user:
                return

            # Get today's tasks
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today_start + timedelta(days=1)

            pending_tasks = Task.query.filter(
                Task.user_id == user_id,
                Task.status == 'pending',
                Task.due_date >= today_start,
                Task.due_date < today_end
            ).order_by(Task.due_date).all()

            if not pending_tasks:
                message = "🎉 <b>صباح الخير!</b>\n\nلا توجد مهام لليوم. استمتع بيومك!"
            else:
                message = f"🌅 <b>صباح الخير!</b>\n\nعندك {len(pending_tasks)} مهام اليوم:\n\n"

                for i, task in enumerate(pending_tasks, 1):
                    priority_emoji = {
                        'high': '🔴',
                        'medium': '🟡',
                        'low': '🟢'
                    }

                    emoji = priority_emoji.get(task.priority, '📝')
                    time_text = task.due_date.strftime('%H:%M') if task.due_date else ''

                    message += f"{i}. {emoji} {task.title}"
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