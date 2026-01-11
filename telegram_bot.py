"""
Telegram Bot for Non Real Assistant
- /user_id - Show user their Telegram ID
- /create_account - Create a new user account
- /create_task - Create a new task
- /today_tasks - Show today's scheduled tasks
"""

from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
import logging
import os
import re
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
SYSTEM_URL = os.getenv('SYSTEM_URL', 'http://localhost:5000')
API_SECRET_KEY = os.getenv('API_SECRET_KEY')

# Conversation states for create_account
MOBILE, EMAIL, NAME, CONFIRM = range(4)

# Conversation states for create_task
TASK_NAME, TASK_DESC, TASK_ASSISTANT, TASK_TIME, TASK_CONFIRM = range(10, 15)


def normalize_phone(phone: str) -> str:
    """Normalize phone number - remove +, spaces, dashes"""
    if not phone:
        return phone
    return phone.replace('+', '').replace(' ', '').replace('-', '').replace('(', '').replace(')', '')


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command - show welcome message"""
    user = update.effective_user

    message = f"""
مرحباً {user.first_name}! 👋

أنا بوت <b>Non Real Assistant</b>

<b>الأوامر المتاحة:</b>
/user_id - عرض معرف التليجرام الخاص بك
/create_account - إنشاء حساب جديد في النظام
/create_task - إنشاء مهمة جديدة
/today_tasks - عرض مهام اليوم
/cancel - إلغاء العملية الحالية
    """

    await update.message.reply_text(message, parse_mode='HTML')


async def show_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user their Telegram ID"""
    user = update.effective_user

    message = f"""
👤 <b>معلومات المستخدم</b>

🆔 <b>معرف التليجرام:</b> <code>{user.id}</code>
👨‍💼 <b>اسم المستخدم:</b> @{user.username if user.username else 'غير متوفر'}
📝 <b>الاسم:</b> {user.first_name} {user.last_name if user.last_name else ''}

💡 <i>يمكنك نسخ المعرف بالضغط عليه</i>
    """

    await update.message.reply_text(message, parse_mode='HTML')


async def today_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show today's scheduled tasks for the user"""
    telegram_user = update.effective_user
    telegram_id = str(telegram_user.id)

    try:
        # Import here to avoid circular imports
        import sys
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

        from app import app
        from models import db, User, Task
        from datetime import datetime, timedelta
        import pytz

        with app.app_context():
            # Find user by telegram_id
            user = User.query.filter_by(telegram_id=telegram_id).first()

            if not user:
                await update.message.reply_text(
                    """
❌ <b>لم يتم العثور على حسابك!</b>

يبدو أن معرف التليجرام الخاص بك غير مرتبط بأي حساب.

استخدم /create_account لإنشاء حساب جديد.
                    """,
                    parse_mode='HTML'
                )
                return

            # Get user timezone
            user_tz = pytz.timezone(user.timezone or 'Africa/Cairo')
            now_local = datetime.now(user_tz)
            today_start = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today_start + timedelta(days=1)

            # Convert to UTC for database query
            today_start_utc = today_start.astimezone(pytz.UTC).replace(tzinfo=None)
            today_end_utc = today_end.astimezone(pytz.UTC).replace(tzinfo=None)

            # Get today's tasks
            tasks = Task.query.filter(
                Task.create_user_id == user.id,
                Task.complete_time.is_(None),
                Task.cancel_time.is_(None),
                Task.time.isnot(None),
                Task.time >= today_start_utc,
                Task.time < today_end_utc
            ).order_by(Task.time).all()

            if not tasks:
                await update.message.reply_text(
                    f"""
🎉 <b>لا توجد مهام مجدولة لليوم!</b>

📅 التاريخ: {now_local.strftime('%Y-%m-%d')}

استمتع بيومك! 🌟
                    """,
                    parse_mode='HTML'
                )
                return

            # Build tasks message
            message = f"""
📋 <b>مهامك لليوم</b>
📅 {now_local.strftime('%Y-%m-%d')}

عندك <b>{len(tasks)}</b> مهام مجدولة:

"""
            for i, task in enumerate(tasks, 1):
                # Convert task time to user timezone
                task_time_utc = pytz.UTC.localize(task.time)
                task_time_local = task_time_utc.astimezone(user_tz)
                time_str = task_time_local.strftime('%H:%M')

                status = "⏰" if task_time_local > now_local else "⚠️"

                message += f"{i}. {status} <b>{task.name}</b> ({time_str})\n"
                if task.description:
                    message += f"   📝 {task.description[:50]}{'...' if len(task.description) > 50 else ''}\n"

            message += "\n💪 يوم موفق!"

            await update.message.reply_text(message, parse_mode='HTML')

    except Exception as e:
        logger.error(f"Error fetching today's tasks: {e}")
        await update.message.reply_text(
            f"❌ حدث خطأ أثناء جلب المهام: {str(e)}",
            parse_mode='HTML'
        )


# ===== Create User Conversation =====

async def create_account_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start user creation process"""
    user = update.effective_user
    telegram_id = str(user.id)

    # Check if telegram_id already has an account
    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from app import app
        from models import User

        with app.app_context():
            existing = User.query.filter_by(telegram_id=telegram_id).first()
            if existing:
                await update.message.reply_text(
                    f"""
⚠️ <b>لديك حساب مسبقاً!</b>

معرف التليجرام الخاص بك مرتبط بالفعل بحساب:
📱 رقم الهاتف: <code>{existing.mobile}</code>

يمكنك تسجيل الدخول مباشرة:
{SYSTEM_URL}
                    """,
                    parse_mode='HTML'
                )
                return ConversationHandler.END
    except Exception as e:
        logger.warning(f"Could not check existing user: {e}")

    # Store telegram info
    context.user_data['telegram_id'] = telegram_id
    context.user_data['telegram_username'] = user.username
    context.user_data['telegram_name'] = f"{user.first_name} {user.last_name or ''}".strip()

    message = """
📝 <b>إنشاء حساب جديد</b>

سنحتاج بعض المعلومات لإنشاء حسابك.

📱 <b>الخطوة 1/3:</b> أدخل رقم الهاتف بالصيغة الدولية
<i>(مثال: +201234567890 أو 201234567890)</i>

⚠️ يجب إدخال مفتاح الدولة (مثل 20 لمصر، 966 للسعودية)

أرسل /cancel للإلغاء
    """

    await update.message.reply_text(message, parse_mode='HTML')
    return MOBILE


async def get_mobile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get mobile number"""
    mobile_input = update.message.text.strip()

    # Normalize phone (remove +, spaces, dashes)
    mobile = normalize_phone(mobile_input)

    # Remove leading 0 if present after country code check
    # Phone must be at least 10 digits (country code + number)
    if not re.match(r'^\d{10,15}$', mobile):
        await update.message.reply_text(
            """❌ رقم الهاتف غير صالح.

يجب إدخال رقم الهاتف بالصيغة الدولية:
• مثال مصر: <code>+201234567890</code> أو <code>201234567890</code>
• مثال السعودية: <code>+966501234567</code> أو <code>966501234567</code>

⚠️ لا تنسَ مفتاح الدولة!

أعد إدخال الرقم:""",
            parse_mode='HTML'
        )
        return MOBILE

    context.user_data['mobile'] = mobile

    message = """
📧 <b>الخطوة 2/3:</b> أدخل البريد الإلكتروني
<i>(اختياري - أرسل "تخطي" للتخطي)</i>
    """

    await update.message.reply_text(message, parse_mode='HTML')
    return EMAIL


async def get_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get email"""
    email_input = update.message.text.strip()

    if email_input.lower() in ['تخطي', 'skip', '-']:
        context.user_data['email'] = None
    else:
        # Simple email validation
        if '@' not in email_input or '.' not in email_input:
            await update.message.reply_text(
                "❌ البريد الإلكتروني غير صالح.\n\nأعد الإدخال أو أرسل 'تخطي':",
                parse_mode='HTML'
            )
            return EMAIL
        context.user_data['email'] = email_input

    # Suggest telegram name as default
    suggested_name = context.user_data.get('telegram_name', '')

    message = f"""
👤 <b>الخطوة 3/3:</b> أدخل اسمك
<i>(اختياري - أرسل "تخطي" لاستخدام اسم التليجرام)</i>

💡 اسمك في التليجرام: <b>{suggested_name}</b>
    """

    await update.message.reply_text(message, parse_mode='HTML')
    return NAME


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get name"""
    name_input = update.message.text.strip()

    if name_input.lower() in ['تخطي', 'skip', '-']:
        context.user_data['name'] = context.user_data.get('telegram_name')
    else:
        context.user_data['name'] = name_input

    # Show confirmation
    data = context.user_data

    message = f"""
✅ <b>تأكيد البيانات</b>

📱 <b>رقم الهاتف:</b> {data['mobile']}
📧 <b>البريد:</b> {data.get('email') or 'غير محدد'}
👤 <b>الاسم:</b> {data.get('name') or 'غير محدد'}
🆔 <b>معرف التليجرام:</b> {data['telegram_id']}

هل البيانات صحيحة؟
أرسل <b>"نعم"</b> للتأكيد أو <b>"لا"</b> للإلغاء
    """

    await update.message.reply_text(message, parse_mode='HTML')
    return CONFIRM


async def confirm_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm and create user"""
    response = update.message.text.strip().lower()

    if response not in ['نعم', 'yes', 'y', '1']:
        await update.message.reply_text(
            "❌ تم إلغاء إنشاء الحساب.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    # Prepare data
    data = context.user_data
    user_data = {
        'mobile': data['mobile'],
        'telegram_id': data['telegram_id'],
        'email': data.get('email'),
        'name': data.get('name')
    }

    # Try to create user via API
    try:
        if API_SECRET_KEY:
            # Use external API
            response = requests.post(
                f"{SYSTEM_URL}/api/external/users",
                json=user_data,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {API_SECRET_KEY}'
                },
                timeout=10
            )

            if response.status_code == 201:
                result = response.json()
                await update.message.reply_text(
                    f"""
✅ <b>تم إنشاء حسابك بنجاح!</b>

🔗 <b>رابط النظام:</b>
{SYSTEM_URL}

📱 استخدم رقم هاتفك للدخول: <code>{data['mobile']}</code>

سيتم إرسال رمز التحقق (OTP) على التليجرام عند تسجيل الدخول.
                    """,
                    parse_mode='HTML',
                    reply_markup=ReplyKeyboardRemove()
                )
            elif response.status_code == 409:
                await update.message.reply_text(
                    f"""
⚠️ <b>رقم الهاتف مسجل مسبقاً!</b>

يمكنك تسجيل الدخول مباشرة:
{SYSTEM_URL}
                    """,
                    parse_mode='HTML',
                    reply_markup=ReplyKeyboardRemove()
                )
            else:
                error = response.json().get('error', 'Unknown error')
                await update.message.reply_text(
                    f"❌ خطأ في إنشاء الحساب: {error}",
                    reply_markup=ReplyKeyboardRemove()
                )
        else:
            # No API key - create directly via database
            await create_account_directly(update, user_data)

    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {e}")
        # Fallback to direct creation
        await create_account_directly(update, user_data)
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        await update.message.reply_text(
            f"❌ حدث خطأ: {str(e)}",
            reply_markup=ReplyKeyboardRemove()
        )

    return ConversationHandler.END


async def create_account_directly(update: Update, user_data: dict):
    """Create user directly in database (fallback)"""
    try:
        # Import here to avoid circular imports
        import sys
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

        from app import app
        from models import db, User

        with app.app_context():
            # Check if exists
            existing = User.query.filter_by(mobile=user_data['mobile']).first()
            if existing:
                await update.message.reply_text(
                    f"""
⚠️ <b>رقم الهاتف مسجل مسبقاً!</b>

يمكنك تسجيل الدخول مباشرة:
{SYSTEM_URL}
                    """,
                    parse_mode='HTML',
                    reply_markup=ReplyKeyboardRemove()
                )
                return

            # Create user
            new_user = User(
                mobile=user_data['mobile'],
                telegram_id=user_data['telegram_id'],
                email=user_data.get('email'),
                name=user_data.get('name')
            )
            db.session.add(new_user)
            db.session.commit()

            await update.message.reply_text(
                f"""
✅ <b>تم إنشاء حسابك بنجاح!</b>

🔗 <b>رابط النظام:</b>
{SYSTEM_URL}

📱 استخدم رقم هاتفك للدخول: <code>{user_data['mobile']}</code>

سيتم إرسال رمز التحقق (OTP) على التليجرام عند تسجيل الدخول.
                """,
                parse_mode='HTML',
                reply_markup=ReplyKeyboardRemove()
            )

    except Exception as e:
        logger.error(f"Direct user creation failed: {e}")
        await update.message.reply_text(
            f"❌ فشل إنشاء الحساب: {str(e)}",
            reply_markup=ReplyKeyboardRemove()
        )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel current operation"""
    context.user_data.clear()
    await update.message.reply_text(
        "❌ تم إلغاء العملية.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


# ===== Create Task Conversation =====

async def create_task_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start task creation process"""
    telegram_user = update.effective_user
    telegram_id = str(telegram_user.id)

    # Check if user has an account
    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from app import app
        from models import User

        with app.app_context():
            user = User.query.filter_by(telegram_id=telegram_id).first()
            if not user:
                await update.message.reply_text(
                    """
❌ <b>لم يتم العثور على حسابك!</b>

يجب إنشاء حساب أولاً باستخدام /create_user
                    """,
                    parse_mode='HTML'
                )
                return ConversationHandler.END

            # Store user info
            context.user_data['user_id'] = user.id
            context.user_data['user_name'] = user.name or user.mobile

    except Exception as e:
        logger.error(f"Error checking user: {e}")
        await update.message.reply_text("❌ حدث خطأ في التحقق من الحساب")
        return ConversationHandler.END

    message = """
📝 <b>إنشاء مهمة جديدة</b>

<b>الخطوة 1/4:</b> أدخل اسم المهمة

أرسل /cancel للإلغاء
    """

    await update.message.reply_text(message, parse_mode='HTML')
    return TASK_NAME


async def get_task_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get task name"""
    task_name = update.message.text.strip()

    if len(task_name) < 2:
        await update.message.reply_text("❌ اسم المهمة قصير جداً. أدخل اسماً أطول:")
        return TASK_NAME

    context.user_data['task_name'] = task_name

    message = """
📋 <b>الخطوة 2/4:</b> أدخل وصف المهمة
<i>(اختياري - أرسل "تخطي" للتخطي)</i>
    """

    await update.message.reply_text(message, parse_mode='HTML')
    return TASK_DESC


async def get_task_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get task description"""
    desc_input = update.message.text.strip()

    if desc_input.lower() in ['تخطي', 'skip', '-']:
        context.user_data['task_desc'] = None
    else:
        context.user_data['task_desc'] = desc_input

    # Get available assistants for this user
    try:
        from app import app
        from models import Assistant

        with app.app_context():
            user_id = context.user_data['user_id']
            assistants = Assistant.query.filter_by(create_user_id=user_id).all()

            if not assistants:
                # No assistants - skip to time
                context.user_data['task_assistant_id'] = None
                message = """
⏰ <b>الخطوة 3/4:</b> أدخل وقت المهمة

أدخل الوقت بصيغة: <code>YYYY-MM-DD HH:MM</code>
مثال: <code>2026-01-12 14:30</code>

أو أرسل "تخطي" لإنشاء مهمة بدون وقت محدد
                """
                await update.message.reply_text(message, parse_mode='HTML')
                return TASK_TIME

            # Build keyboard with assistants
            keyboard = []
            context.user_data['assistants'] = {}
            for assistant in assistants:
                context.user_data['assistants'][str(assistant.id)] = assistant.name
                keyboard.append([InlineKeyboardButton(assistant.name, callback_data=f"assistant_{assistant.id}")])

            keyboard.append([InlineKeyboardButton("بدون مساعد ❌", callback_data="assistant_none")])

            reply_markup = InlineKeyboardMarkup(keyboard)

            message = """
🤖 <b>الخطوة 3/4:</b> اختر المساعد

اختر المساعد المسؤول عن هذه المهمة:
            """

            await update.message.reply_text(message, parse_mode='HTML', reply_markup=reply_markup)
            return TASK_ASSISTANT

    except Exception as e:
        logger.error(f"Error getting assistants: {e}")
        context.user_data['task_assistant_id'] = None
        message = """
⏰ <b>الخطوة 3/4:</b> أدخل وقت المهمة

أدخل الوقت بصيغة: <code>YYYY-MM-DD HH:MM</code>
مثال: <code>2026-01-12 14:30</code>
        """
        await update.message.reply_text(message, parse_mode='HTML')
        return TASK_TIME


async def select_assistant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle assistant selection callback"""
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "assistant_none":
        context.user_data['task_assistant_id'] = None
        context.user_data['task_assistant_name'] = "بدون مساعد"
    else:
        assistant_id = data.replace("assistant_", "")
        context.user_data['task_assistant_id'] = int(assistant_id)
        context.user_data['task_assistant_name'] = context.user_data['assistants'].get(assistant_id, "مساعد")

    message = """
⏰ <b>الخطوة 4/4:</b> أدخل وقت المهمة

أدخل الوقت بصيغة: <code>YYYY-MM-DD HH:MM</code>
مثال: <code>2026-01-12 14:30</code>

أو أرسل "تخطي" لإنشاء مهمة بدون وقت محدد
    """

    await query.edit_message_text(message, parse_mode='HTML')
    return TASK_TIME


async def get_task_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get task time"""
    from datetime import datetime
    import pytz

    time_input = update.message.text.strip()

    if time_input.lower() in ['تخطي', 'skip', '-']:
        context.user_data['task_time'] = None
    else:
        # Parse time
        try:
            # Try different formats
            for fmt in ['%Y-%m-%d %H:%M', '%d-%m-%Y %H:%M', '%Y/%m/%d %H:%M']:
                try:
                    task_time = datetime.strptime(time_input, fmt)
                    break
                except ValueError:
                    continue
            else:
                await update.message.reply_text(
                    """❌ صيغة الوقت غير صحيحة.

استخدم الصيغة: <code>YYYY-MM-DD HH:MM</code>
مثال: <code>2026-01-12 14:30</code>

أعد إدخال الوقت:""",
                    parse_mode='HTML'
                )
                return TASK_TIME

            # Store as UTC (assume user input is in Cairo timezone)
            cairo_tz = pytz.timezone('Africa/Cairo')
            local_time = cairo_tz.localize(task_time)
            utc_time = local_time.astimezone(pytz.UTC).replace(tzinfo=None)
            context.user_data['task_time'] = utc_time
            context.user_data['task_time_display'] = time_input

        except Exception as e:
            logger.error(f"Error parsing time: {e}")
            await update.message.reply_text("❌ خطأ في معالجة الوقت. أعد المحاولة:")
            return TASK_TIME

    # Show confirmation
    data = context.user_data

    message = f"""
✅ <b>تأكيد المهمة</b>

📝 <b>الاسم:</b> {data['task_name']}
📋 <b>الوصف:</b> {data.get('task_desc') or 'غير محدد'}
🤖 <b>المساعد:</b> {data.get('task_assistant_name', 'بدون مساعد')}
⏰ <b>الوقت:</b> {data.get('task_time_display') or 'غير محدد'}

هل البيانات صحيحة؟
أرسل <b>"نعم"</b> للتأكيد أو <b>"لا"</b> للإلغاء
    """

    await update.message.reply_text(message, parse_mode='HTML')
    return TASK_CONFIRM


async def confirm_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm and create task"""
    response = update.message.text.strip().lower()

    if response not in ['نعم', 'yes', 'y', '1']:
        await update.message.reply_text(
            "❌ تم إلغاء إنشاء المهمة.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    # Create task
    try:
        from app import app
        from models import db, Task

        with app.app_context():
            data = context.user_data

            new_task = Task(
                name=data['task_name'],
                description=data.get('task_desc'),
                create_user_id=data['user_id'],
                assistant_id=data.get('task_assistant_id'),
                time=data.get('task_time')
            )
            db.session.add(new_task)
            db.session.commit()

            task_id = new_task.id
            task_link = f"{SYSTEM_URL}/tasks/{task_id}"

            await update.message.reply_text(
                f"""
✅ <b>تم إنشاء المهمة بنجاح!</b>

📝 <b>{data['task_name']}</b>

🔗 <a href="{task_link}">فتح المهمة في المتصفح</a>
                """,
                parse_mode='HTML',
                reply_markup=ReplyKeyboardRemove()
            )

    except Exception as e:
        logger.error(f"Error creating task: {e}")
        await update.message.reply_text(
            f"❌ حدث خطأ في إنشاء المهمة: {str(e)}",
            reply_markup=ReplyKeyboardRemove()
        )

    return ConversationHandler.END


def main():
    """Start the bot"""
    if not BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not set in .env")
        return

    # Create application
    application = Application.builder().token(BOT_TOKEN).build()

    # Create user conversation handler (supports both create_account and create_user commands)
    create_account_handler = ConversationHandler(
        entry_points=[
            CommandHandler("create_account", create_account_start),
            CommandHandler("create_user", create_account_start)
        ],
        states={
            MOBILE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_mobile)],
            EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_email)],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_creation)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Create task conversation handler
    create_task_handler = ConversationHandler(
        entry_points=[CommandHandler("create_task", create_task_start)],
        states={
            TASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_task_name)],
            TASK_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_task_desc)],
            TASK_ASSISTANT: [CallbackQueryHandler(select_assistant, pattern="^assistant_")],
            TASK_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_task_time)],
            TASK_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_task)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("user_id", show_user_id))
    application.add_handler(CommandHandler("today_tasks", today_tasks))
    application.add_handler(create_account_handler)
    application.add_handler(create_task_handler)
    application.add_handler(CommandHandler("cancel", cancel))

    # Start the bot
    print(f"🤖 Bot is running...")
    print(f"📡 System URL: {SYSTEM_URL}")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
