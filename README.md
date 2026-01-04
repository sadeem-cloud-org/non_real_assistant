# Non Real Assistant

مساعد شخصي ذكي محلي مع تسجيل دخول آمن عبر OTP على تيليجرام

## المميزات

### الأساسية
- تسجيل دخول آمن عن طريق OTP عبر Telegram
- واجهة عربية/إنجليزية مع دعم RTL/LTR
- قاعدة بيانات SQLite
- جلسات آمنة

### إدارة المساعدين
- أنواع مساعدين متعددة (مدير مهام، تذكيرات، أتمتة، مراقبة سيرفرات، جمع بيانات)
- ربط المهام والسكريبتات بالمساعدين
- جدولة وتنفيذ تلقائي (run_every)
- إشعارات مخصصة لكل مساعد

### السكريبتات
- محرر كود متكامل (Python, JavaScript, Bash)
- تنفيذ السكريبتات مع تتبع النتائج
- إرسال نتائج التنفيذ إلى Telegram
- إرسال نتائج التنفيذ إلى البريد الإلكتروني
- روابط مشاركة عامة لنتائج التنفيذ

### الإشعارات
- إشعارات Telegram تلقائية للتذكيرات (على مستوى المساعد)
- إشعارات البريد الإلكتروني (على مستوى المساعد)
- إشعارات المتصفح
- قوالب إشعارات مخصصة

### دعم متعدد اللغات
- واجهة عربية وإنجليزية
- تبديل اللغة من الواجهة

### دعم متعدد المستخدمين
- كل مستخدم له بياناته الخاصة
- إعدادات شخصية (اللغة، المنطقة الزمنية، الإشعارات)
- سجل تسجيل الدخول
- إعدادات النظام

## المتطلبات

- Python 3.8+
- Telegram Bot Token

## التثبيت

### 1. تثبيت المكتبات

```bash
cd non_real_assistant
pip install -r requirements.txt
```

### 2. إعداد Telegram Bot

1. افتح [@BotFather](https://t.me/botfather) في تيليجرام
2. أرسل `/newbot`
3. اتبع التعليمات لإنشاء البوت
4. احفظ الـ Token

### 3. إعداد ملف البيئة

```bash
cp .env.example .env
```

ثم عدّل ملف `.env`:

```env
SECRET_KEY=your-random-secret-key-here
TELEGRAM_BOT_TOKEN=your-telegram-bot-token-here
```

### 4. التحقق من إعدادات البوت

```bash
python bot_info.py
```

### 5. بدء محادثة مع البوت

**يجب عليك بدء محادثة مع البوت قبل تسجيل الدخول!**

1. افتح الرابط الذي ظهر من الأمر السابق
2. اضغط على "Start" أو أرسل أي رسالة للبوت

### 6. معرفة Telegram ID الخاص بك

1. أرسل رسالة لـ [@userinfobot](https://t.me/userinfobot)
2. سيعطيك الـ ID الخاص بك

### 7. تحديث قاعدة البيانات

```bash
python -m migrations.migrate
```

هذا الأمر سيقوم بـ:
- إنشاء جميع الجداول
- إضافة اللغات (العربية، الإنجليزية)
- إضافة أنواع المساعدين
- إضافة قوالب الإشعارات

### 8. إنشاء مستخدم

```bash
python create_user.py create --phone 01234567890 --telegram_id YOUR_TELEGRAM_ID
```

### 9. تشغيل التطبيق

```bash
python app.py
```

افتح المتصفح على: `http://localhost:5000`

## البنية

```
non_real_assistant/
├── app.py                      # نقطة الدخول الرئيسية
├── models.py                   # نماذج قاعدة البيانات
├── scheduler.py                # جدولة المهام والسكريبتات
│
├── config/
│   ├── __init__.py
│   └── settings.py             # إعدادات التطبيق
│
├── routes/
│   ├── __init__.py             # تسجيل الـ Blueprints
│   ├── auth.py                 # المصادقة وتسجيل الدخول
│   ├── dashboard.py            # لوحة التحكم
│   ├── tasks.py                # إدارة المهام
│   ├── assistants.py           # إدارة المساعدين
│   ├── scripts.py              # إدارة السكريبتات
│   ├── executions.py           # سجل التنفيذ
│   ├── settings.py             # إعدادات المستخدم والنظام
│   ├── share.py                # روابط المشاركة العامة
│   └── api.py                  # API Endpoints
│
├── services/
│   ├── __init__.py
│   ├── auth.py                 # خدمات المصادقة
│   ├── telegram_bot.py         # إرسال رسائل Telegram
│   ├── email_service.py        # إرسال البريد الإلكتروني
│   └── script_executor.py      # تنفيذ السكريبتات
│
├── migrations/
│   ├── __init__.py
│   └── migrate.py              # تحديث قاعدة البيانات
│
├── static/
│   ├── css/
│   └── js/
│       ├── theme.js            # إدارة الثيم
│       ├── dashboard.js
│       ├── tasks.js
│       ├── assistants.js
│       ├── scripts.js
│       └── executions.js
│
└── templates/
    ├── base.html               # القالب الأساسي
    ├── login.html
    ├── dashboard.html
    ├── tasks.html
    ├── assistants.html
    ├── scripts.html
    ├── executions.html
    ├── settings.html           # إعدادات المستخدم
    ├── system_settings.html    # إعدادات النظام
    ├── share_execution.html    # صفحة المشاركة العامة
    └── share_not_found.html
```

## قاعدة البيانات

### الجداول:
- **languages** - اللغات المدعومة (ar, en)
- **system_settings** - إعدادات النظام (telegram_bot_token, otp_expiration, etc.)
- **users** - المستخدمين (mobile, name, telegram_id, email, timezone, language_id)
- **user_login_history** - سجل تسجيل الدخول
- **otps** - رموز التحقق
- **notify_templates** - قوالب الإشعارات
- **assistant_types** - أنواع المساعدين (name, related_action)
- **assistants** - المساعدين (telegram_notify, email_notify, run_every, next_run_time)
- **tasks** - المهام (مربوطة بالمساعدين، name, time, complete_time, cancel_time)
- **scripts** - السكريبتات (مربوطة بالمساعدين)
- **script_execute_logs** - سجل تنفيذ السكريبتات (share_token, is_public)

## API Endpoints

### المصادقة
- `POST /login` - تسجيل الدخول
- `POST /verify-otp` - التحقق من OTP
- `GET /logout` - تسجيل الخروج

### المساعدين
- `GET /api/assistants` - قائمة المساعدين
- `POST /api/assistants` - إنشاء مساعد
- `PUT /api/assistants/:id` - تحديث مساعد
- `DELETE /api/assistants/:id` - حذف مساعد
- `GET /api/assistant-types` - أنواع المساعدين

### المهام
- `GET /api/tasks` - قائمة المهام
- `POST /api/tasks` - إنشاء مهمة
- `PUT /api/tasks/:id` - تحديث مهمة
- `DELETE /api/tasks/:id` - حذف مهمة
- `POST /api/tasks/:id/complete` - إتمام مهمة
- `POST /api/tasks/:id/cancel` - إلغاء مهمة

### السكريبتات
- `GET /api/scripts` - قائمة السكريبتات
- `POST /api/scripts` - إنشاء سكريبت
- `PUT /api/scripts/:id` - تحديث سكريبت
- `DELETE /api/scripts/:id` - حذف سكريبت
- `POST /api/scripts/:id/run` - تشغيل سكريبت

### التنفيذ
- `GET /api/executions` - سجل التنفيذ
- `GET /api/executions/:id` - تفاصيل تنفيذ

### المشاركة
- `POST /api/executions/:id/share` - إنشاء رابط مشاركة
- `DELETE /api/executions/:id/share` - إزالة المشاركة
- `GET /share/execution/:token` - صفحة المشاركة العامة

### الإعدادات
- `GET /api/user/profile` - بيانات المستخدم
- `PUT /api/user/profile` - تحديث البيانات
- `GET /api/system/settings` - إعدادات النظام
- `PUT /api/system/settings` - تحديث إعدادات النظام
- `GET /api/languages` - قائمة اللغات

### اللغة
- `GET /set-language/ar` - تبديل للعربية
- `GET /set-language/en` - تبديل للإنجليزية

## الأمان

- جميع OTP صالحة لمدة 5 دقائق فقط (قابلة للتخصيص)
- الأكواد المستخدمة يتم إلغاؤها تلقائياً
- الجلسات محمية بـ SECRET_KEY
- لا يتم تخزين كلمات المرور
- روابط المشاركة عشوائية وآمنة
- سجل تسجيل الدخول (IP, Browser)

## حل المشاكل الشائعة

### Chat not found
البوت لا يستطيع إرسال رسائل للمستخدم - تأكد من بدء محادثة مع البوت أولاً

### Bot is blocked by user
المستخدم حظر البوت - ألغِ الحظر من تيليجرام

### Invalid phone number
رقم الهاتف غير مسجل - استخدم `python create_user.py list` للتحقق

## الترخيص

هذا مشروع شخصي - استخدمه كما تشاء!
