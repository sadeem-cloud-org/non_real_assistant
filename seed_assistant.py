#!/usr/bin/env python3
"""
Seed database with example assistant (Reminder)
Usage: python seed_assistant.py
"""

from app import app
from models import db, AssistantType, Action

# مثال سكريبت المنبه اليومي
DAILY_REMINDER_SCRIPT = '''
import json
import sys
from datetime import datetime

def get_daily_tasks(user_id):
    """جلب مهام اليوم من الداتابيز"""
    # TODO: سيتم ربطه بالداتابيز فعلياً
    # هذا مثال فقط
    tasks = [
        {"title": "مراجعة الكود", "time": "12:00", "priority": "high"},
        {"title": "اجتماع مع الفريق", "time": "15:00", "priority": "medium"},
        {"title": "كتابة التوثيق", "time": "17:00", "priority": "low"}
    ]
    return tasks

def main():
    try:
        # قراءة المدخلات
        input_data = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}
        user_id = input_data.get('user_id')

        # تنفيذ العملية
        tasks = get_daily_tasks(user_id)

        # تكوين الرسالة
        if tasks:
            message = f"🌅 صباح الخير! عندك {len(tasks)} مهام النهاردة:\\n\\n"
            for task in tasks:
                emoji = "🔴" if task['priority'] == 'high' else "🟡" if task['priority'] == 'medium' else "🟢"
                message += f"{emoji} {task['title']} ({task['time']})\\n"
            message += "\\n💪 يلا نبدأ يوم منتج!"
        else:
            message = "🎉 مفيش مهام النهاردة! استمتع بيومك"

        # إرجاع النتيجة
        result = {
            "success": True,
            "message": message,
            "data": {
                "tasks_count": len(tasks),
                "tasks": tasks
            },
            "notification": {
                "type": "info",
                "title": "مهام اليوم",
                "body": message,
                "send_telegram": True,
                "send_web": False
            }
        }

        print(json.dumps(result, ensure_ascii=False))

    except Exception as e:
        error_result = {
            "success": False,
            "message": f"حدث خطأ: {str(e)}",
            "notification": {
                "type": "error",
                "title": "خطأ",
                "body": f"فشل تنفيذ المنبه: {str(e)}",
                "send_telegram": False,
                "send_web": True
            }
        }
        print(json.dumps(error_result, ensure_ascii=False))

if __name__ == "__main__":
    main()
'''

# مثال سكريبت تذكير قبل الموعد
BEFORE_TASK_REMINDER_SCRIPT = '''
import json
import sys
from datetime import datetime, timedelta

def get_upcoming_tasks(user_id, minutes_ahead=15):
    """جلب المهام القادمة خلال الدقائق القادمة"""
    # TODO: سيتم ربطه بالداتابيز فعلياً
    # هذا مثال فقط
    upcoming = [
        {"title": "اجتماع مهم", "time": "15:00", "minutes_left": 15}
    ]
    return upcoming

def main():
    try:
        input_data = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}
        user_id = input_data.get('user_id')
        minutes_ahead = input_data.get('minutes_ahead', 15)

        tasks = get_upcoming_tasks(user_id, minutes_ahead)

        if tasks:
            task = tasks[0]
            message = f"⏰ تذكير: {task['title']} بعد {task['minutes_left']} دقيقة!\\n\\nاستعد للموعد 📅"

            result = {
                "success": True,
                "message": message,
                "data": {"task": task},
                "notification": {
                    "type": "warning",
                    "title": "تذكير بموعد قريب",
                    "body": message,
                    "send_telegram": True,
                    "send_web": True
                }
            }
        else:
            result = {
                "success": True,
                "message": "لا توجد مهام قريبة",
                "data": {},
                "notification": None
            }

        print(json.dumps(result, ensure_ascii=False))

    except Exception as e:
        error_result = {
            "success": False,
            "message": f"حدث خطأ: {str(e)}",
            "notification": {
                "type": "error",
                "title": "خطأ",
                "body": f"فشل التذكير: {str(e)}",
                "send_telegram": False,
                "send_web": True
            }
        }
        print(json.dumps(error_result, ensure_ascii=False))

if __name__ == "__main__":
    main()
'''


def seed_reminder_assistant():
    """إضافة مساعد المنبه كمثال"""
    with app.app_context():
        # فحص إذا كان موجود بالفعل
        existing = AssistantType.query.filter_by(name='reminder').first()
        if existing:
            print("⚠️  مساعد المنبه موجود بالفعل")
            return

        # إنشاء نوع المساعد
        reminder_type = AssistantType(
            name='reminder',
            display_name_ar='المنبه',
            display_name_en='Reminder',
            description='مساعد ذكي يذكرك بمهامك ومواعيدك اليومية',
            icon='⏰',
            is_active=True
        )

        db.session.add(reminder_type)
        db.session.flush()  # للحصول على الـ ID

        # إنشاء الأكشن الأول: التذكير اليومي الصباحي
        daily_reminder = Action(
            assistant_type_id=reminder_type.id,
            name='daily_morning_reminder',
            display_name='التذكير الصباحي اليومي',
            description='يرسل ملخص بمهام اليوم كل صباح الساعة 8:00',
            execution_type='python_script',
            script_content=DAILY_REMINDER_SCRIPT,
            trigger_type='scheduled',
            trigger_config=json.dumps({
                'cron': '0 8 * * *',  # كل يوم الساعة 8 صباحاً
                'timezone': 'Africa/Cairo'
            }),
            output_format=json.dumps({
                'success': 'boolean',
                'message': 'string',
                'data': 'object',
                'notification': 'object'
            }),
            timeout=30,
            is_active=True
        )

        # إنشاء الأكشن الثاني: تذكير قبل المهمة
        before_task = Action(
            assistant_type_id=reminder_type.id,
            name='before_task_reminder',
            display_name='تذكير قبل المهمة',
            description='يذكرك بالمهام قبل موعدها بـ 15 دقيقة',
            execution_type='python_script',
            script_content=BEFORE_TASK_REMINDER_SCRIPT,
            trigger_type='scheduled',
            trigger_config=json.dumps({
                'cron': '*/15 * * * *',  # كل 15 دقيقة
                'timezone': 'Africa/Cairo'
            }),
            output_format=json.dumps({
                'success': 'boolean',
                'message': 'string',
                'data': 'object',
                'notification': 'object'
            }),
            timeout=30,
            is_active=True
        )

        db.session.add(daily_reminder)
        db.session.add(before_task)
        db.session.commit()

        print("✅ تم إضافة مساعد المنبه بنجاح!")
        print(f"\n📋 التفاصيل:")
        print(f"   - النوع: {reminder_type.display_name_ar}")
        print(f"   - الرمز: {reminder_type.icon}")
        print(f"   - عدد الإجراءات: 2")
        print(f"\n💡 الإجراءات المتاحة:")
        print(f"   1. {daily_reminder.display_name}")
        print(f"      └─ يعمل: كل يوم الساعة 8:00 صباحاً")
        print(f"   2. {before_task.display_name}")
        print(f"      └─ يعمل: كل 15 دقيقة")
        print(f"\n🎯 الخطوة التالية:")
        print(f"   يمكن للمستخدمين الآن إضافة هذا المساعد من لوحة التحكم")


if __name__ == '__main__':
    import json

    seed_reminder_assistant()