#!/usr/bin/env python3
"""Seed assistant types into database"""

import sys

sys.path.insert(0, '/mnt/user-data/outputs/non_real_assistant')

from app import app, db
from models import AssistantType


def seed_assistant_types():
    """Create default assistant types"""

    types = [
        {
            'name': 'task_manager',
            'display_name_ar': 'مدير مهام',
            'display_name_en': 'Task Manager',
            'description': 'يدير المهام اليومية ويرسل التذكيرات',
            'icon': '✅'
        },
        {
            'name': 'reminder',
            'display_name_ar': 'تذكيرات',
            'display_name_en': 'Reminder',
            'description': 'يرسل تذكيرات بالمواعيد والمهام المهمة',
            'icon': '🔔'
        },
        {
            'name': 'automation',
            'display_name_ar': 'أتمتة',
            'display_name_en': 'Automation',
            'description': 'ينفذ مهام أوتوماتيكية حسب الجدول',
            'icon': '🤖'
        },
        {
            'name': 'data_collector',
            'display_name_ar': 'جمع بيانات',
            'display_name_en': 'Data Collector',
            'description': 'يجمع البيانات من مصادر مختلفة',
            'icon': '📊'
        },
        {
            'name': 'custom',
            'display_name_ar': 'مخصص',
            'display_name_en': 'Custom',
            'description': 'مساعد مخصص حسب احتياجاتك',
            'icon': '⚙️'
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