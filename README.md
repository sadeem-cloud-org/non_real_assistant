# Non Real Assistant

مساعد شخصي ذكي لإدارة المهام والسكريبتات مع إشعارات تليجرام

## المميزات

- إدارة المهام مع تذكيرات تلقائية
- تنفيذ سكريبتات (Python, Bash, JavaScript)
- إشعارات عبر Telegram
- واجهة عربية/إنجليزية
- تسجيل دخول آمن عبر OTP

---

## التشغيل السريع

### 1. إعداد Telegram Bot

1. افتح [@BotFather](https://t.me/botfather) في تليجرام
2. أرسل `/newbot` واتبع التعليمات
3. احفظ الـ Token

### 2. إعداد ملف البيئة

```bash
cp .env.example .env
```

عدّل `.env`:
```env
SECRET_KEY=your-secret-key-here
TELEGRAM_BOT_TOKEN=your-bot-token-here
```

---

## التشغيل بـ Docker (موصى به)

```bash
# تشغيل التطبيق
docker-compose up -d

# أو باستخدام make
make prod
```

التطبيق يعمل على: `http://localhost`

### أوامر مفيدة

```bash
make dev          # وضع التطوير
make prod         # وضع الإنتاج
make logs         # عرض السجلات
make down         # إيقاف الخدمات
```

---

## التشغيل من المصدر

### 1. تثبيت المتطلبات

```bash
pip install -r requirements.txt
```

### 2. إعداد قاعدة البيانات

```bash
python -m migrations.migrate
```

### 3. تشغيل التطبيق

```bash
python app.py
```

التطبيق يعمل على: `http://localhost:5000`

### 4. تشغيل البوت (اختياري)

```bash
python telegram_bot.py
```

---

## إنشاء أول مستخدم

### عبر بوت التليجرام
1. افتح البوت
2. أرسل `/create_account`
3. اتبع التعليمات

### عبر سطر الأوامر
```bash
# مع Docker
docker-compose exec web python create_user.py create --phone 01234567890 --telegram_id YOUR_ID --is_admin

# بدون Docker
python create_user.py create --phone 01234567890 --telegram_id YOUR_ID --is_admin
```

**لمعرفة Telegram ID:** أرسل `/user_id` للبوت

---

## أوامر البوت

| الأمر | الوصف |
|-------|-------|
| `/start` | بدء المحادثة |
| `/user_id` | عرض معرف التليجرام |
| `/create_account` | إنشاء حساب جديد |
| `/today_tasks` | عرض مهام اليوم |

---

## قواعد البيانات المدعومة

- **SQLite** (افتراضي) - بدون إعدادات
- **PostgreSQL** - `make prod-pg`
- **MariaDB** - `make prod-mysql`

---

## المزيد

للتفاصيل التقنية والـ API، راجع [DEVELOPMENT.md](DEVELOPMENT.md)
