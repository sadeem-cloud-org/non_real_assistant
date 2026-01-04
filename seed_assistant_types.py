#!/usr/bin/env python3
"""Seed assistant types into database"""

from app import app
from models import db
from models import AssistantType


def seed_assistant_types():
    """Create default assistant types"""

    types = [
        {
            'name': 'task_manager',
            'display_name_ar': 'مدير مهام',
            'display_name_en': 'Task Manager',
            'description': 'يدير المهام اليومية ويرسل التذكيرات',
            'description_ar': 'يدير المهام اليومية ويرسل التذكيرات',
            'description_en': 'Manages daily tasks and sends reminders',
            'icon': 'checkbox',
            'color': 'blue'
        },
        {
            'name': 'reminder',
            'display_name_ar': 'تذكيرات',
            'display_name_en': 'Reminder',
            'description': 'يرسل تذكيرات بالمواعيد والمهام المهمة',
            'description_ar': 'يرسل تذكيرات بالمواعيد والمهام المهمة',
            'description_en': 'Sends reminders for appointments and important tasks',
            'icon': 'bell',
            'color': 'yellow'
        },
        {
            'name': 'automation',
            'display_name_ar': 'أتمتة',
            'display_name_en': 'Automation',
            'description': 'ينفذ مهام أوتوماتيكية حسب الجدول',
            'description_ar': 'ينفذ مهام أوتوماتيكية حسب الجدول',
            'description_en': 'Executes automated tasks according to schedule',
            'icon': 'robot',
            'color': 'purple'
        },
        {
            'name': 'server_monitor',
            'display_name_ar': 'مراقبة السيرفرات',
            'display_name_en': 'Server Monitor',
            'description': 'يراقب حالة السيرفرات ويرسل تقارير',
            'description_ar': 'يراقب حالة السيرفرات ويرسل تقارير',
            'description_en': 'Monitors server status and sends reports',
            'icon': 'server',
            'color': 'green'
        },
        {
            'name': 'data_collector',
            'display_name_ar': 'جمع بيانات',
            'display_name_en': 'Data Collector',
            'description': 'يجمع البيانات من مصادر مختلفة',
            'description_ar': 'يجمع البيانات من مصادر مختلفة',
            'description_en': 'Collects data from various sources',
            'icon': 'chart-bar',
            'color': 'cyan'
        },
        {
            'name': 'notification',
            'display_name_ar': 'إشعارات',
            'display_name_en': 'Notification',
            'description': 'يرسل إشعارات عبر قنوات مختلفة',
            'description_ar': 'يرسل إشعارات عبر قنوات مختلفة',
            'description_en': 'Sends notifications through various channels',
            'icon': 'notification',
            'color': 'orange'
        },
        {
            'name': 'custom',
            'display_name_ar': 'مخصص',
            'display_name_en': 'Custom',
            'description': 'مساعد مخصص حسب احتياجاتك',
            'description_ar': 'مساعد مخصص حسب احتياجاتك',
            'description_en': 'Custom assistant according to your needs',
            'icon': 'settings',
            'color': 'gray'
        }
    ]

    with app.app_context():
        # Check if types already exist
        existing = AssistantType.query.count()
        if existing > 0:
            print(f"✅ Assistant types already exist ({existing} types)")
            return

        # Create types
        for type_data in types:
            assistant_type = AssistantType(**type_data)
            db.session.add(assistant_type)

        db.session.commit()
        print(f"✅ Created {len(types)} assistant types")

        # Show created types
        all_types = AssistantType.query.all()
        for t in all_types:
            print(f"  {t.id}. {t.icon} {t.display_name_ar} ({t.name})")


if __name__ == '__main__':
    seed_assistant_types()