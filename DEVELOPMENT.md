# Non Real Assistant

مساعد شخصي ذكي محلي مع تسجيل دخول آمن عبر OTP على تيليجرام

## المميزات

### الأساسية
- تسجيل دخول آمن عن طريق OTP عبر Telegram
- واجهة عربية/إنجليزية مع دعم RTL/LTR
- دعم قواعد بيانات متعددة (SQLite, PostgreSQL, MariaDB)
- جلسات آمنة
- دعم Docker مع nginx reverse proxy

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
- ملفات ترجمة .po قابلة للتخصيص
- تحميل الترجمات من ملفات أو قاعدة البيانات

### بوت التليجرام
- `/user_id` - معرفة Telegram ID الخاص بك
- `/create_account` - إنشاء حساب جديد مباشرة من البوت
- يعمل تلقائياً مع Docker

### دعم متعدد المستخدمين
- كل مستخدم له بياناته الخاصة
- إعدادات شخصية (اللغة، المنطقة الزمنية، الإشعارات)
- سجل تسجيل الدخول
- إعدادات النظام

## المتطلبات

- Python 3.8+ (للتشغيل المحلي)
- Docker و Docker Compose (للتشغيل بـ Docker)
- Telegram Bot Token

---

## التشغيل باستخدام Docker (موصى به)

### 1. إعداد ملف البيئة

```bash
cp .env.example .env
```

عدّل ملف `.env` وأضف:

```env
SECRET_KEY=your-random-secret-key-here
TELEGRAM_BOT_TOKEN=your-telegram-bot-token-here
API_SECRET_KEY=your-api-key-for-bot
SYSTEM_URL=http://localhost
```

### 2. اختيار قاعدة البيانات

#### SQLite (افتراضي - بدون إعدادات إضافية)
```bash
docker-compose up -d
```

#### PostgreSQL
```bash
# أضف في .env:
DATABASE_URL=postgresql://nra_user:nra_password@postgres:5432/non_real_assistant
POSTGRES_PASSWORD=change-this-password

# ثم شغّل:
docker-compose --profile postgres up -d
```

#### MariaDB
```bash
# أضف في .env:
DATABASE_URL=mysql+pymysql://nra_user:nra_password@mariadb:3306/non_real_assistant
MYSQL_PASSWORD=change-this-password
MYSQL_ROOT_PASSWORD=change-this-root-password

# ثم شغّل:
docker-compose --profile mariadb up -d
```

### 3. أوامر Makefile المفيدة

```bash
# تطوير (بدون nginx)
make dev

# إنتاج مع SQLite
make prod

# إنتاج مع PostgreSQL
make prod-pg

# إنتاج مع MariaDB
make prod-mysql

# عرض السجلات
make logs

# إيقاف الخدمات
make down

# الدخول لقاعدة البيانات
make psql      # PostgreSQL
make mysql     # MariaDB
```

### 4. الخدمات التي تعمل

| الخدمة | الوصف | المنفذ |
|--------|-------|--------|
| web | تطبيق Flask | 5000 (داخلي) |
| bot | بوت التليجرام | - |
| nginx | Reverse Proxy | 80, 443 |
| postgres | قاعدة بيانات (اختياري) | 5432 |
| mariadb | قاعدة بيانات (اختياري) | 3306 |

### 5. إنشاء أول مستخدم

**الطريقة الأولى: عبر بوت التليجرام**
1. افتح البوت وأرسل `/create_account`
2. اتبع التعليمات لإدخال رقم الهاتف والبيانات

**الطريقة الثانية: عبر سطر الأوامر**
```bash
docker-compose exec web python create_user.py create --phone 01234567890 --telegram_id YOUR_ID --is_admin
```

---

## التثبيت المحلي (بدون Docker)

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

**الطريقة الأولى (باستخدام البوت الخاص بالتطبيق):**
1. افتح البوت الخاص بك
2. أرسل `/user_id`
3. سيعطيك الـ ID الخاص بك

**الطريقة الثانية:**
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
# مستخدم عادي
python create_user.py create --phone 01234567890 --telegram_id YOUR_TELEGRAM_ID

# مستخدم مدير (Admin)
python create_user.py create --phone 01234567890 --telegram_id YOUR_TELEGRAM_ID --is_admin

# مع الاسم
python create_user.py create --phone 01234567890 --telegram_id YOUR_TELEGRAM_ID --name "اسم المستخدم"
```

**ملاحظة:** المستخدم المدير (Admin) يمكنه الوصول لصفحة إدارة الترجمات.

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
├── telegram_bot.py             # بوت التليجرام (مستقل)
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
│   ├── translations.py         # إدارة الترجمات
│   ├── share.py                # روابط المشاركة العامة
│   └── api.py                  # API Endpoints
│
├── services/
│   ├── __init__.py
│   ├── auth.py                 # خدمات المصادقة
│   ├── telegram_bot.py         # إرسال رسائل Telegram
│   ├── email_service.py        # إرسال البريد الإلكتروني
│   ├── translation_service.py  # خدمة الترجمة
│   └── script_executor.py      # تنفيذ السكريبتات
│
├── migrations/
│   ├── __init__.py
│   └── migrate.py              # تحديث قاعدة البيانات
│
├── translations/               # ملفات الترجمة
│   ├── ar.po                   # الترجمة العربية
│   └── en.po                   # الترجمة الإنجليزية
│
├── nginx/                      # إعدادات nginx
│   └── nginx.conf
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
├── templates/
│   ├── base.html               # القالب الأساسي
│   ├── login.html
│   ├── dashboard.html
│   ├── tasks.html
│   ├── assistants.html
│   ├── scripts.html
│   ├── executions.html
│   ├── settings.html           # إعدادات المستخدم
│   ├── system_settings.html    # إعدادات النظام
│   ├── translations.html       # إدارة الترجمات
│   ├── share_execution.html    # صفحة المشاركة العامة
│   └── share_not_found.html
│
├── Dockerfile                  # ملف Docker
├── docker-compose.yml          # إنتاج مع nginx
├── docker-compose.dev.yml      # تطوير بدون nginx
├── Makefile                    # أوامر مختصرة
├── .env.example                # مثال متغيرات البيئة
└── .dockerignore
```

## قاعدة البيانات

### قواعد البيانات المدعومة

| قاعدة البيانات | الاستخدام | ملاحظات |
|----------------|-----------|---------|
| SQLite | افتراضي، تطوير | بدون إعدادات إضافية |
| PostgreSQL | إنتاج | أداء أفضل، مناسب للاستخدام الكثيف |
| MariaDB | إنتاج | بديل مفتوح المصدر لـ MySQL |

### الجداول:
- **languages** - اللغات المدعومة (ar, en)
- **translations** - الترجمات (key, value, language_id)
- **key_value_settings** - إعدادات النظام (key-value)
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

### إدارة الترجمات (مدير فقط)
- `GET /api/translations/languages` - قائمة اللغات
- `POST /api/translations/languages` - إضافة لغة جديدة
- `DELETE /api/translations/languages/:id` - حذف لغة
- `GET /api/translations/:language_id` - ترجمات لغة معينة
- `PUT /api/translations/:language_id` - تحديث ترجمة
- `GET /api/translations/:language_id/export` - تصدير ملف .po
- `POST /api/translations/:language_id/import` - استيراد ملف .po
- `POST /api/translations/:language_id/sync` - مزامنة النصوص
- `GET /api/translations/files` - قائمة ملفات .po المتاحة
- `POST /api/translations/load-from-files` - تحميل الترجمات من الملفات

### إعدادات البريد الإلكتروني (مدير فقط)
- `GET /api/system/email-settings` - الحصول على إعدادات SMTP
- `PUT /api/system/email-settings` - تحديث إعدادات SMTP
- `POST /api/system/email-test` - اختبار إعدادات SMTP

### API الخارجي (External API)

#### إنشاء مستخدم جديد

```http
POST /api/external/users
```

**المصادقة:**
يتطلب مفتاح API في الـ headers:
- `Authorization: Bearer YOUR_API_KEY` أو
- `X-API-Key: YOUR_API_KEY`

**إعداد مفتاح API:**
أضف في ملف `.env`:
```env
API_SECRET_KEY=your-secure-api-key-here
```

**الطلب:**
```json
{
    "mobile": "01234567890",
    "name": "اسم المستخدم",
    "email": "user@example.com",
    "telegram_id": "123456789",
    "is_admin": false
}
```

| الحقل | النوع | مطلوب | الوصف |
|-------|------|-------|-------|
| mobile | string | ✅ | رقم الهاتف (فريد) |
| name | string | ❌ | اسم المستخدم |
| email | string | ❌ | البريد الإلكتروني |
| telegram_id | string | ❌ | معرف تيليجرام |
| is_admin | boolean | ❌ | هل المستخدم مدير (افتراضي: false) |

**الاستجابة الناجحة (201):**
```json
{
    "success": true,
    "user": {
        "id": 1,
        "mobile": "01234567890",
        "name": "اسم المستخدم",
        "email": "user@example.com",
        "telegram_id": "123456789",
        "is_admin": false
    }
}
```

**أخطاء محتملة:**

| الكود | الوصف |
|-------|-------|
| 400 | رقم الهاتف مطلوب |
| 401 | مفتاح API غير صالح |
| 409 | رقم الهاتف مسجل مسبقاً |
| 503 | API غير مُفعّل (API_SECRET_KEY غير موجود) |

**مثال باستخدام curl:**
```bash
curl -X POST http://localhost:5000/api/external/users \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{"mobile": "01234567890", "name": "مستخدم جديد", "telegram_id": "123456789"}'
```

**مثال باستخدام Python:**
```python
import requests

response = requests.post(
    'http://localhost:5000/api/external/users',
    headers={
        'Content-Type': 'application/json',
        'Authorization': 'Bearer your-api-key'
    },
    json={
        'mobile': '01234567890',
        'name': 'مستخدم جديد',
        'telegram_id': '123456789'
    }
)
print(response.json())
```

## بوت التليجرام

البوت يعمل كخدمة مستقلة ويوفر:

### الأوامر المتاحة

| الأمر | الوصف |
|-------|-------|
| `/start` | بدء المحادثة مع البوت |
| `/user_id` | عرض Telegram ID الخاص بك |
| `/create_account` | إنشاء حساب جديد (محادثة تفاعلية) |
| `/cancel` | إلغاء العملية الحالية |

### إنشاء حساب عبر البوت

1. أرسل `/create_account` للبوت
2. أدخل رقم الهاتف
3. أدخل البريد الإلكتروني (اختياري - أرسل "تخطي")
4. أدخل الاسم (اختياري - أرسل "تخطي")
5. تأكيد البيانات

**ملاحظة:** يتطلب وجود `API_SECRET_KEY` في ملف `.env` لعمل أمر `/create_account`.

## متغيرات البيئة

| المتغير | مطلوب | الوصف |
|---------|-------|-------|
| `SECRET_KEY` | ✅ | مفتاح Flask السري |
| `TELEGRAM_BOT_TOKEN` | ✅ | توكن بوت التليجرام |
| `API_SECRET_KEY` | ❌ | مفتاح API الخارجي |
| `SYSTEM_URL` | ❌ | رابط النظام (للبوت) |
| `DATABASE_URL` | ❌ | رابط قاعدة البيانات |
| `FLASK_ENV` | ❌ | بيئة Flask (development/production) |
| `POSTGRES_*` | ❌ | إعدادات PostgreSQL |
| `MYSQL_*` | ❌ | إعدادات MariaDB |

## الأمان

- جميع OTP صالحة لمدة 5 دقائق فقط (قابلة للتخصيص)
- الأكواد المستخدمة يتم إلغاؤها تلقائياً
- الجلسات محمية بـ SECRET_KEY
- لا يتم تخزين كلمات المرور
- روابط المشاركة عشوائية وآمنة
- سجل تسجيل الدخول (IP, Browser)
- Rate limiting عبر nginx (API: 10r/s, Login: 5r/m)
- Security headers (X-Frame-Options, X-Content-Type-Options, X-XSS-Protection)

## حل المشاكل الشائعة

### Chat not found
البوت لا يستطيع إرسال رسائل للمستخدم - تأكد من بدء محادثة مع البوت أولاً

### Bot is blocked by user
المستخدم حظر البوت - ألغِ الحظر من تيليجرام

### Invalid phone number
رقم الهاتف غير مسجل - استخدم `python create_user.py list` للتحقق

## الترخيص

هذا مشروع شخصي - استخدمه كما تشاء!
