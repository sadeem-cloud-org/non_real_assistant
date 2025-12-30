# Script API Documentation

## نظرة عامة

هذا الدليل يشرح كيفية كتابة سكريبتات للمساعدين في Non Real Assistant.

## بنية السكريبت

كل سكريبت يجب أن:
1. يقرأ البيانات من `sys.argv[1]` كـ JSON
2. ينفذ المهمة المطلوبة
3. يطبع النتيجة كـ JSON في `stdout`

## Output Format

```json
{
  "success": true|false,
  "message": "رسالة للمستخدم",
  "data": {
    // أي بيانات إضافية
  },
  "notification": {
    "type": "info|success|warning|error",
    "title": "عنوان الإشعار",
    "body": "نص الرسالة التفصيلي",
    "send_telegram": true|false,
    "send_web": true|false
  }
}
```

## Input Format

السكريبت يستقبل JSON object يحتوي على:

```json
{
  "user_id": 123,
  "assistant_id": 456,
  // أي بيانات أخرى حسب الحاجة
}
```

## مثال: سكريبت بسيط

```python
import json
import sys
from datetime import datetime

def main():
    try:
        # قراءة المدخلات
        input_data = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}
        user_id = input_data.get('user_id')
        
        # تنفيذ المهمة
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        message = f"مرحباً! الوقت الحالي: {current_time}"
        
        # إرجاع النتيجة
        result = {
            "success": True,
            "message": message,
            "data": {
                "timestamp": current_time,
                "user_id": user_id
            },
            "notification": {
                "type": "info",
                "title": "تحديث الوقت",
                "body": message,
                "send_telegram": True,
                "send_web": False
            }
        }
        
        print(json.dumps(result, ensure_ascii=False))
        
    except Exception as e:
        # في حالة الخطأ
        error_result = {
            "success": False,
            "message": f"حدث خطأ: {str(e)}",
            "notification": {
                "type": "error",
                "title": "خطأ",
                "body": f"فشل التنفيذ: {str(e)}",
                "send_telegram": False,
                "send_web": True
            }
        }
        print(json.dumps(error_result, ensure_ascii=False))

if __name__ == "__main__":
    main()
```

## أنواع الإشعارات

### info ℹ️
معلومات عامة للمستخدم

```python
"notification": {
    "type": "info",
    "title": "معلومة",
    "body": "رسالة معلوماتية",
    "send_telegram": True
}
```

### success ✅
عملية نجحت بنجاح

```python
"notification": {
    "type": "success",
    "title": "نجح",
    "body": "تمت العملية بنجاح",
    "send_telegram": True
}
```

### warning ⚠️
تحذير يحتاج انتباه

```python
"notification": {
    "type": "warning",
    "title": "تحذير",
    "body": "انتبه لهذا الأمر",
    "send_telegram": True
}
```

### error ❌
خطأ حدث أثناء التنفيذ

```python
"notification": {
    "type": "error",
    "title": "خطأ",
    "body": "فشلت العملية",
    "send_telegram": True
}
```

## الوصول إلى قاعدة البيانات

لاستخدام قاعدة البيانات في السكريبت:

```python
import json
import sys

# إضافة مسار المشروع
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db, Task, User

def get_user_tasks(user_id):
    """جلب مهام المستخدم"""
    with app.app_context():
        tasks = Task.query.filter_by(
            user_id=user_id,
            status='pending'
        ).all()
        return [task.to_dict() for task in tasks]

def main():
    input_data = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}
    user_id = input_data.get('user_id')
    
    tasks = get_user_tasks(user_id)
    
    result = {
        "success": True,
        "message": f"عندك {len(tasks)} مهام معلقة",
        "data": {"tasks": tasks}
    }
    
    print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    main()
```

## Security Best Practices

### ✅ افعل:
- استخدم `try/except` دائماً
- تحقق من صحة المدخلات
- استخدم timeout مناسب
- أرجع JSON دائماً
- اكتب رسائل خطأ واضحة

### ❌ لا تفعل:
- لا تستخدم `eval()` أو `exec()`
- لا تقرأ ملفات خارج مجلد المشروع
- لا تفتح اتصالات شبكة غير آمنة
- لا تخزن بيانات حساسة في المتغيرات
- لا تعمل infinite loops

## Timeout

- الافتراضي: 60 ثانية
- يمكن تعديله في جدول Actions
- السكريبت سيتوقف تلقائياً بعد انتهاء المهلة

## Error Handling

يجب التعامل مع جميع الأخطاء:

```python
try:
    # الكود الرئيسي
    pass
except ValueError as e:
    # خطأ في القيمة
    result = {"success": False, "message": f"قيمة غير صحيحة: {e}"}
except KeyError as e:
    # مفتاح مفقود
    result = {"success": False, "message": f"بيانات ناقصة: {e}"}
except Exception as e:
    # أي خطأ آخر
    result = {"success": False, "message": f"خطأ غير متوقع: {e}"}
finally:
    print(json.dumps(result, ensure_ascii=False))
```

## Testing

لاختبار السكريبت:

```bash
# إنشاء ملف test_input.json
echo '{"user_id": 1, "assistant_id": 1}' > test_input.json

# تنفيذ السكريبت
python3 your_script.py "$(cat test_input.json)"
```

## أمثلة متقدمة

### مثال: فحص السيرفر

```python
import json
import sys
import subprocess

def ping_server(host):
    """فحص حالة السيرفر"""
    try:
        result = subprocess.run(
            ['ping', '-c', '1', '-W', '2', host],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except:
        return False

def main():
    input_data = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}
    server = input_data.get('server', 'localhost')
    
    is_online = ping_server(server)
    
    if is_online:
        result = {
            "success": True,
            "message": f"✅ السيرفر {server} يعمل بشكل طبيعي",
            "data": {"server": server, "status": "online"},
            "notification": {
                "type": "success",
                "title": "السيرفر متصل",
                "body": f"السيرفر {server} يعمل",
                "send_telegram": False
            }
        }
    else:
        result = {
            "success": False,
            "message": f"❌ السيرفر {server} لا يستجيب!",
            "data": {"server": server, "status": "offline"},
            "notification": {
                "type": "error",
                "title": "تحذير: السيرفر معطل",
                "body": f"السيرفر {server} لا يستجيب!",
                "send_telegram": True
            }
        }
    
    print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    main()
```

## المزيد من المساعدة

- راجع ملف `seed_assistant.py` للأمثلة
- انظر إلى `script_executor.py` لفهم آلية التنفيذ
- اقرأ `models.py` لمعرفة بنية قاعدة البيانات