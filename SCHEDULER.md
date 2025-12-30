# Task Scheduler - التذكيرات التلقائية

## نظرة عامة

الـ Scheduler يعمل في الخلفية (background thread) ويفحص المهام كل دقيقة ويرسل تذكيرات تلقائية على Telegram.

## المميزات

### 1. تذكيرات المهام التلقائية ⏰

- يفحص المهام كل دقيقة
- يرسل تذكير قبل موعد المهمة بـ 0-2 دقيقة
- يتجنب إرسال تذكيرات مكررة
- رسائل مخصصة حسب:
  - عنوان المهمة
  - الوصف
  - الأولوية (🔴 عالية، 🟡 متوسطة، 🟢 منخفضة)
  - وقت الاستحقاق

### 2. ملخص يومي 📅

دالة جاهزة لإرسال ملخص بمهام اليوم:
- عدد المهام المعلقة
- ترتيب حسب الوقت
- رسالة تحفيزية

## كيفية الاستخدام

### التشغيل التلقائي

الـ Scheduler يبدأ تلقائياً مع تشغيل التطبيق:

```python
# في app.py
from scheduler import start_scheduler
scheduler = start_scheduler(app)
```

### اختبار الملخص اليومي

```bash
# عبر API
curl -X POST http://localhost:5000/api/test/daily-summary \
  -H "Cookie: session=YOUR_SESSION"
```

أو من Dashboard → في console:

```javascript
fetch('/api/test/daily-summary', {method: 'POST'})
  .then(r => r.json())
  .then(d => console.log(d));
```

### إيقاف الـ Scheduler

```python
from scheduler import stop_scheduler
stop_scheduler()
```

## مثال رسالة تذكير

```
⏰ تذكير بمهمة

🔴 مراجعة كود المشروع

📋 مراجعة PR #123 قبل نهاية اليوم

📅 موعد الاستحقاق: 2024-12-30 15:00

⏱ بعد 15 دقيقة

💪 حان وقت إنجاز هذه المهمة!
```

## مثال ملخص يومي

```
🌅 صباح الخير!

عندك 3 مهام اليوم:

1. 🔴 مراجعة الكود (12:00)
2. 🟡 اجتماع مع الفريق (15:00)
3. 🟢 كتابة التوثيق (17:00)

💪 يلا نبدأ يوم منتج!
```

## البنية التقنية

### TaskScheduler Class

```python
class TaskScheduler:
    def __init__(self, app):
        # تهيئة الـ scheduler
        
    def start(self):
        # بدء الـ background thread
        
    def stop(self):
        # إيقاف الـ scheduler
        
    def _check_task_reminders(self):
        # فحص المهام وإرسال التذكيرات
        
    def send_daily_summary(self, user_id):
        # إرسال ملخص يومي
```

### Reminder Tracking

لتجنب التكرار، يستخدم الـ Scheduler حقل `extra_data` في المهمة:

```json
{
  "reminder_sent": true,
  "reminder_sent_at": "2024-12-30T10:00:00"
}
```

## التخصيص

### تغيير وقت الفحص

```python
# في scheduler.py، _run_loop method
time.sleep(60)  # غير إلى 30 للفحص كل 30 ثانية
```

### تغيير نطاق التذكير

```python
# في _check_task_reminders method
Task.reminder_time <= now + timedelta(minutes=2)  # غير 2 إلى 5 مثلاً
```

### إضافة جدولة لإجراءات أخرى

```python
def _run_loop(self):
    while self.running:
        with self.app.app_context():
            self._check_task_reminders()
            self._check_scheduled_actions()  # أضف هنا
            self._send_morning_summaries()   # مثال
        
        time.sleep(60)
```

## إضافة ملخص صباحي تلقائي

لإرسال ملخص كل صباح الساعة 8:00:

```python
def _run_loop(self):
    while self.running:
        with self.app.app_context():
            self._check_task_reminders()
            
            # Check if it's 8:00 AM
            now = datetime.utcnow()
            if now.hour == 8 and now.minute == 0:
                self._send_all_daily_summaries()
        
        time.sleep(60)

def _send_all_daily_summaries(self):
    """Send daily summary to all users with active assistants"""
    from models import User, Assistant
    
    # Get all users with active reminder assistant
    users = User.query.join(Assistant).filter(
        Assistant.is_enabled == True,
        Assistant.assistant_type_id == 1  # Reminder type
    ).distinct().all()
    
    for user in users:
        try:
            self.send_daily_summary(user.id)
        except Exception as e:
            print(f"Error sending summary to user {user.id}: {e}")
```

## Logging

الـ Scheduler يطبع رسائل في console:

```
✅ Task Scheduler started
✅ Sent reminder for task #1 to user #1
❌ Failed to send reminder for task #2: Chat not found
✅ Sent daily summary to user #1
```

## Security

- ✅ User isolation (كل مستخدم يشوف مهامه فقط)
- ✅ Thread-safe database operations
- ✅ Error handling لتجنب crash الـ scheduler
- ✅ Daemon thread (يتوقف مع توقف التطبيق)

## Performance

- **Memory:** ~5-10 MB
- **CPU:** < 1% (معظم الوقت sleeping)
- **Database:** Query كل دقيقة فقط
- **Network:** فقط عند وجود تذكيرات

## Troubleshooting

### الـ Scheduler لا يرسل تذكيرات

1. تأكد من تشغيل التطبيق بـ `python app.py`
2. تأكد من رؤية رسالة "✅ Task Scheduler started"
3. تحقق من وجود مهام برموز تذكير
4. تحقق من أن user بدأ chat مع البوت

### رسائل مكررة

**تم الحل!** الـ Scheduler الآن:
- ✅ يفحص نطاق زمني أضيق (1 دقيقة بدل 2)
- ✅ يتحقق من timestamp آخر إرسال
- ✅ يمنع الإرسال المكرر لمدة 5 دقائق
- ✅ يحفظ وقت الإرسال بدقة

**للتجربة:**
إذا أردت إعادة اختبار تذكير نفس المهمة:
```bash
# Reset reminder status
curl -X POST http://localhost:5000/api/tasks/TASK_ID/reset-reminder \
  -H "Cookie: session=YOUR_SESSION"
```

### استهلاك عالي للموارد

- قلل تكرار الفحص (من 60 إلى 120 ثانية مثلاً)
- أضف indexes على `reminder_time` في database

## Future Enhancements

- [ ] Cron expressions للإجراءات المجدولة
- [ ] Retry logic عند فشل الإرسال
- [ ] Queue system للرسائل
- [ ] Analytics للتذكيرات
- [ ] Web dashboard للـ scheduler status
- [ ] Multiple timezone support
- [ ] Snooze functionality

---

**الـ Scheduler يعمل الآن! 🎉**

كل مهمة بوقت تذكير ستصلك رسالة على Telegram تلقائياً!