# Non Real Assistant

A smart personal assistant for managing tasks and scripts with Telegram notifications.

مساعد شخصي ذكي لإدارة المهام والسكريبتات مع إشعارات تليجرام

---

## Features | المميزات

### Task Management | إدارة المهام
- Create, edit, and organize tasks with deadlines
- Set reminders with customizable notification times
- Mark tasks as complete or cancelled
- Share tasks publicly with unique links
- Attach files to tasks (images, documents, etc.)
- Filter tasks by status (pending, completed, cancelled)
- Switch between card and list views

### Script Execution | تنفيذ السكريبتات
- Support for multiple languages: **Python**, **Bash**, **JavaScript**
- Execute scripts locally or on remote servers via SSH
- Real-time execution output viewing
- Execution history with detailed logs
- Run scripts directly from the editor

### Remote Server Management | إدارة الخوادم البعيدة
- Add and manage SSH servers
- Execute scripts on remote machines
- Support for password and SSH key authentication
- Test connection before saving

### Assistants | المساعدين
- Create task-based or script-based assistants
- Customize notification settings per assistant
- Enable/disable Telegram and email notifications
- Set notification templates

### Notifications | الإشعارات
- **Telegram notifications** for task reminders
- **Browser push notifications**
- **Email notifications** (SMTP configuration)
- Notification log for tracking all sent notifications

### User Interface | واجهة المستخدم
- Modern, responsive design using Tabler UI
- **Arabic (RTL)** and **English (LTR)** support
- Dark/Light theme toggle
- Profile with avatar upload
- Mobile-friendly interface

### Security | الأمان
- OTP-based login (no passwords)
- Session management
- Admin panel for user management
- Secure file uploads

---

## Quick Start | التشغيل السريع

### 1. Setup Telegram Bot | إعداد بوت التليجرام

1. Open [@BotFather](https://t.me/botfather) in Telegram
2. Send `/newbot` and follow instructions
3. Save the Bot Token

### 2. Environment Setup | إعداد ملف البيئة

```bash
cp .env.example .env
```

Edit `.env`:
```env
SECRET_KEY=your-secret-key-here
TELEGRAM_BOT_TOKEN=your-bot-token-here
```

---

## Running with Docker (Recommended) | التشغيل بـ Docker

```bash
# Start the application
docker-compose up -d

# Or using make
make prod
```

Application runs at: `http://localhost`

### Useful Commands | أوامر مفيدة

| Command | Description |
|---------|-------------|
| `make dev` | Development mode |
| `make prod` | Production mode |
| `make logs` | View logs |
| `make down` | Stop services |
| `make prod-pg` | Production with PostgreSQL |
| `make prod-mysql` | Production with MariaDB |

---

## Running from Source | التشغيل من المصدر

### 1. Install Requirements | تثبيت المتطلبات

```bash
pip install -r requirements.txt
```

### 2. Setup Database | إعداد قاعدة البيانات

```bash
python -m migrations.migrate
```

### 3. Run Application | تشغيل التطبيق

```bash
python app.py
```

Application runs at: `http://localhost:5000`

### 4. Run Telegram Bot (Optional) | تشغيل البوت

```bash
python telegram_bot.py
```

---

## User Guide | دليل الاستخدام

### Creating Your First Account | إنشاء أول حساب

#### Via Telegram Bot:
1. Open the bot
2. Send `/create_account`
3. Follow the instructions

#### Via Command Line:
```bash
# With Docker
docker-compose exec web python create_user.py create --phone 01234567890 --telegram_id YOUR_ID --is_admin

# Without Docker
python create_user.py create --phone 01234567890 --telegram_id YOUR_ID --is_admin
```

**To get your Telegram ID:** Send `/user_id` to the bot

---

### Dashboard | لوحة التحكم

The dashboard provides an overview of:
- **Active Assistants** - Number of assistants in the last 7 days
- **Pending Tasks** - Tasks awaiting completion
- **Completed Today** - Tasks completed today
- **Recent Operations** - Latest script executions

Quick actions available:
- View pending tasks with action buttons (complete, cancel, delete)
- View recent script execution results

---

### Managing Tasks | إدارة المهام

#### Creating a Task:
1. Go to **Tasks** page
2. Click **Add Task** button
3. Fill in:
   - Task name
   - Select assistant
   - Due date and time (optional)
   - Reminder settings
   - Attachments (optional)
4. Click **Save**

#### Task Actions:
- **Complete** - Mark task as done
- **Cancel** - Cancel the task
- **Edit** - Modify task details
- **Delete** - Remove task permanently
- **Share** - Generate public link

#### View Modes:
- **Cards View** - Visual card layout
- **List View** - Compact table layout

---

### Managing Scripts | إدارة السكريبتات

#### Creating a Script:
1. Go to **Scripts** page
2. Click **Add Script** button
3. Fill in:
   - Script name
   - Select language (Python/Bash/JavaScript)
   - Select assistant
   - Choose execution target (Local or SSH Server)
   - Write your code
4. Click **Save**

#### Running a Script:
- Click the **Run** button on any script
- View output in the execution panel
- Check execution history in **Execution Log**

#### SSH Server Setup:
1. Go to **Admin Dashboard** > **SSH Servers**
2. Add new server with:
   - Server name
   - Host and port
   - Username
   - Authentication (password or SSH key)
3. Test connection before saving

---

### Profile & Settings | الملف الشخصي والإعدادات

Access from the user menu dropdown:

#### Profile Section:
- Upload/change profile avatar
- Update name and email
- Change phone number
- Update Telegram ID

#### Preferences Section:
- Change language (Arabic/English)
- Set timezone
- Enable/disable browser notifications

#### Account Info:
- View registration date
- View user ID

---

### Notifications | الإشعارات

#### Notification Channels:
1. **Telegram** - Instant messages via bot
2. **Browser** - Push notifications
3. **Email** - SMTP-based emails

#### Setting Up Notifications:
1. Enable notifications per assistant
2. Configure notification templates
3. Set reminder times for tasks

#### Viewing Notification History:
- Go to **Notifications Log**
- Filter by type, status, or date
- View delivery status

---

## Bot Commands | أوامر البوت

| Command | Description |
|---------|-------------|
| `/start` | Start conversation |
| `/user_id` | Show your Telegram ID |
| `/create_account` | Create new account |
| `/today_tasks` | View today's tasks |

---

## Supported Databases | قواعد البيانات المدعومة

| Database | Command | Notes |
|----------|---------|-------|
| SQLite | Default | No configuration needed |
| PostgreSQL | `make prod-pg` | Recommended for production |
| MariaDB | `make prod-mysql` | MySQL compatible |

---

## API Endpoints | نقاط الـ API

### Tasks
- `GET /api/tasks` - List all tasks
- `POST /api/tasks` - Create task
- `GET /api/tasks/<id>` - Get task details
- `PUT /api/tasks/<id>` - Update task
- `DELETE /api/tasks/<id>` - Delete task
- `POST /api/tasks/<id>/complete` - Mark complete
- `POST /api/tasks/<id>/cancel` - Cancel task

### Scripts
- `GET /api/scripts` - List all scripts
- `POST /api/scripts` - Create script
- `POST /api/scripts/<id>/execute` - Run script
- `GET /api/executions` - Execution history

### User
- `GET /api/user/profile` - Get profile
- `PUT /api/user/profile` - Update profile
- `POST /api/user/avatar` - Upload avatar
- `DELETE /api/user/avatar` - Remove avatar

---

## File Structure | هيكل الملفات

```
non_real_assistant/
├── app.py                 # Main application
├── config.py              # Configuration
├── models.py              # Database models
├── telegram_bot.py        # Telegram bot
├── routes/                # Route handlers
│   ├── auth.py           # Authentication
│   ├── tasks.py          # Task management
│   ├── scripts.py        # Script management
│   ├── settings.py       # User settings
│   └── admin.py          # Admin panel
├── templates/             # HTML templates
├── static/               # Static files
│   ├── css/              # Stylesheets
│   ├── js/               # JavaScript
│   └── uploads/          # User uploads
├── migrations/           # Database migrations
└── docker-compose.yml    # Docker configuration
```

---

## Environment Variables | متغيرات البيئة

| Variable | Description | Required |
|----------|-------------|----------|
| `SECRET_KEY` | Flask secret key | Yes |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | Yes |
| `DATABASE_URL` | Database connection URL | No (SQLite default) |
| `SMTP_HOST` | Email server host | No |
| `SMTP_PORT` | Email server port | No |
| `SMTP_USER` | Email username | No |
| `SMTP_PASS` | Email password | No |

---

## Troubleshooting | حل المشاكل

### Common Issues:

**Bot not responding:**
- Check if `TELEGRAM_BOT_TOKEN` is correct
- Ensure bot service is running

**Tasks not showing:**
- Clear browser cache
- Check browser console for errors

**Avatar upload fails:**
- Maximum size is 2MB
- Supported formats: PNG, JPG, JPEG, GIF, WEBP

**SSH connection fails:**
- Verify server credentials
- Check firewall settings
- Test connection using the "Test" button

---

## Contributing | المساهمة

Contributions are welcome! Please feel free to submit pull requests.

---

## License | الرخصة

This project is licensed under the MIT License.

---

## Support | الدعم

For issues and feature requests, please open an issue on GitHub.

For more technical details, see [DEVELOPMENT.md](DEVELOPMENT.md)
