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
from datetime import datetime
import pytz
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

# Bot message translations
BOT_MESSAGES = {
    'ar': {
        'welcome': "مرحباً {name}! 👋\n\nأنا بوت <b>Non Real Assistant</b>\n\n<b>الأوامر المتاحة:</b>\n/user_id - عرض معرف التليجرام الخاص بك\n/create_account - إنشاء حساب جديد في النظام\n/create_task - إنشاء مهمة جديدة\n/today_tasks - عرض مهام اليوم\n/cancel - إلغاء العملية الحالية",
        'user_info': "👤 <b>معلومات المستخدم</b>\n\n🆔 <b>معرف التليجرام:</b> <code>{telegram_id}</code>\n👨‍💼 <b>اسم المستخدم:</b> @{username}\n📝 <b>الاسم:</b> {full_name}\n\n💡 <i>يمكنك نسخ المعرف بالضغط عليه</i>",
        'no_account': "❌ <b>لم يتم العثور على حسابك!</b>\n\nيبدو أن معرف التليجرام الخاص بك غير مرتبط بأي حساب.\n\nاستخدم /create_account لإنشاء حساب جديد.",
        'already_has_account': "⚠️ <b>لديك حساب مسبقاً!</b>\n\nمعرف التليجرام الخاص بك مرتبط بالفعل بحساب:\n📱 رقم الهاتف: <code>{mobile}</code>\n\nيمكنك تسجيل الدخول مباشرة:\n{url}",
        'create_account_start': "📝 <b>إنشاء حساب جديد</b>\n\nسنحتاج بعض المعلومات لإنشاء حسابك.\n\n📱 <b>الخطوة 1/3:</b> أدخل رقم الهاتف بالصيغة الدولية\n<i>(مثال: +201234567890 أو 201234567890)</i>\n\n⚠️ يجب إدخال مفتاح الدولة (مثل 20 لمصر، 966 للسعودية)\n\nأرسل /cancel للإلغاء",
        'invalid_phone': "❌ رقم الهاتف غير صالح.\n\nيجب إدخال رقم الهاتف بالصيغة الدولية:\n• مثال مصر: <code>+201234567890</code> أو <code>201234567890</code>\n• مثال السعودية: <code>+966501234567</code> أو <code>966501234567</code>\n\n⚠️ لا تنسَ مفتاح الدولة!\n\nأعد إدخال الرقم:",
        'enter_email': "📧 <b>الخطوة 2/3:</b> أدخل البريد الإلكتروني\n<i>(اختياري - أرسل \"تخطي\" للتخطي)</i>",
        'invalid_email': "❌ البريد الإلكتروني غير صالح.\n\nأعد الإدخال أو أرسل 'تخطي':",
        'enter_name': "👤 <b>الخطوة 3/3:</b> أدخل اسمك\n<i>(اختياري - أرسل \"تخطي\" لاستخدام اسم التليجرام)</i>\n\n💡 اسمك في التليجرام: <b>{telegram_name}</b>",
        'confirm_data': "✅ <b>تأكيد البيانات</b>\n\n📱 <b>رقم الهاتف:</b> {mobile}\n📧 <b>البريد:</b> {email}\n👤 <b>الاسم:</b> {name}\n🆔 <b>معرف التليجرام:</b> {telegram_id}\n\nهل البيانات صحيحة؟\nأرسل <b>\"نعم\"</b> للتأكيد أو <b>\"لا\"</b> للإلغاء",
        'account_created': "✅ <b>تم إنشاء حسابك بنجاح!</b>\n\n🔗 <b>رابط النظام:</b>\n{url}\n\n📱 استخدم رقم هاتفك للدخول: <code>{mobile}</code>\n\nسيتم إرسال رمز التحقق (OTP) على التليجرام عند تسجيل الدخول.",
        'phone_exists': "⚠️ <b>رقم الهاتف مسجل مسبقاً!</b>\n\nيمكنك تسجيل الدخول مباشرة:\n{url}",
        'cancelled': "❌ تم إلغاء العملية.",
        'creation_cancelled': "❌ تم إلغاء إنشاء الحساب.",
        'task_creation_cancelled': "❌ تم إلغاء إنشاء المهمة.",
        'no_tasks_today': "🎉 <b>لا توجد مهام مجدولة لليوم!</b>\n\n📅 التاريخ: {date}\n\nاستمتع بيومك! 🌟",
        'tasks_today': "📋 <b>مهامك لليوم</b>\n📅 {date}\n\nعندك <b>{count}</b> مهام مجدولة:\n\n",
        'have_a_good_day': "\n💪 يوم موفق!",
        'create_task_start': "📝 <b>إنشاء مهمة جديدة</b>\n\n<b>الخطوة 1/4:</b> أدخل اسم المهمة\n\nأرسل /cancel للإلغاء",
        'task_name_short': "❌ اسم المهمة قصير جداً. أدخل اسماً أطول:",
        'enter_task_desc': "📋 <b>الخطوة 2/4:</b> أدخل وصف المهمة\n<i>(اختياري - أرسل \"تخطي\" للتخطي)</i>",
        'select_assistant': "🤖 <b>الخطوة 3/4:</b> اختر المساعد\n\nاختر المساعد المسؤول عن هذه المهمة:",
        'no_assistant': "بدون مساعد ❌",
        'enter_task_time': "⏰ <b>الخطوة {step}/4:</b> أدخل وقت المهمة\n\nأدخل الوقت بصيغة: <code>YYYY-MM-DD HH:MM</code>\nمثال: <code>{example_date}</code>\n\nأو أرسل \"تخطي\" لإنشاء مهمة بدون وقت محدد",
        'invalid_time': "❌ صيغة الوقت غير صحيحة.\n\nاستخدم الصيغة: <code>YYYY-MM-DD HH:MM</code>\nمثال: <code>{example_date}</code>\n\nأعد إدخال الوقت:",
        'time_error': "❌ خطأ في معالجة الوقت. أعد المحاولة:",
        'confirm_task': "✅ <b>تأكيد المهمة</b>\n\n📝 <b>الاسم:</b> {name}\n📋 <b>الوصف:</b> {desc}\n🤖 <b>المساعد:</b> {assistant}\n⏰ <b>الوقت:</b> {time}\n\nهل البيانات صحيحة؟\nأرسل <b>\"نعم\"</b> للتأكيد أو <b>\"لا\"</b> للإلغاء",
        'task_created': "✅ <b>تم إنشاء المهمة بنجاح!</b>\n\n📝 <b>{name}</b>\n\n🔗 <a href=\"{link}\">فتح المهمة في المتصفح</a>",
        'task_error': "❌ حدث خطأ في إنشاء المهمة: {error}",
        'error_checking_account': "❌ حدث خطأ في التحقق من الحساب",
        'not_specified': "غير محدد",
        'not_available': "غير متوفر",
        'skip': 'تخطي',
        'yes_values': ['نعم', 'yes', 'y', '1'],
    },
    'en': {
        'welcome': "Hello {name}! 👋\n\nI'm the <b>Non Real Assistant</b> bot\n\n<b>Available commands:</b>\n/user_id - Show your Telegram ID\n/create_account - Create a new account\n/create_task - Create a new task\n/today_tasks - Show today's tasks\n/cancel - Cancel current operation",
        'user_info': "👤 <b>User Information</b>\n\n🆔 <b>Telegram ID:</b> <code>{telegram_id}</code>\n👨‍💼 <b>Username:</b> @{username}\n📝 <b>Name:</b> {full_name}\n\n💡 <i>You can copy the ID by clicking on it</i>",
        'no_account': "❌ <b>Account not found!</b>\n\nYour Telegram ID is not linked to any account.\n\nUse /create_account to create a new account.",
        'already_has_account': "⚠️ <b>You already have an account!</b>\n\nYour Telegram ID is already linked to an account:\n📱 Phone: <code>{mobile}</code>\n\nYou can login directly:\n{url}",
        'create_account_start': "📝 <b>Create New Account</b>\n\nWe need some information to create your account.\n\n📱 <b>Step 1/3:</b> Enter your phone number in international format\n<i>(Example: +201234567890 or 201234567890)</i>\n\n⚠️ Don't forget the country code (e.g., 20 for Egypt, 966 for Saudi Arabia)\n\nSend /cancel to cancel",
        'invalid_phone': "❌ Invalid phone number.\n\nPlease enter the phone number in international format:\n• Egypt example: <code>+201234567890</code> or <code>201234567890</code>\n• Saudi example: <code>+966501234567</code> or <code>966501234567</code>\n\n⚠️ Don't forget the country code!\n\nRe-enter the number:",
        'enter_email': "📧 <b>Step 2/3:</b> Enter your email\n<i>(Optional - send \"skip\" to skip)</i>",
        'invalid_email': "❌ Invalid email.\n\nRe-enter or send 'skip':",
        'enter_name': "👤 <b>Step 3/3:</b> Enter your name\n<i>(Optional - send \"skip\" to use Telegram name)</i>\n\n💡 Your Telegram name: <b>{telegram_name}</b>",
        'confirm_data': "✅ <b>Confirm Data</b>\n\n📱 <b>Phone:</b> {mobile}\n📧 <b>Email:</b> {email}\n👤 <b>Name:</b> {name}\n🆔 <b>Telegram ID:</b> {telegram_id}\n\nIs the data correct?\nSend <b>\"yes\"</b> to confirm or <b>\"no\"</b> to cancel",
        'account_created': "✅ <b>Account created successfully!</b>\n\n🔗 <b>System URL:</b>\n{url}\n\n📱 Use your phone to login: <code>{mobile}</code>\n\nYou will receive an OTP on Telegram when logging in.",
        'phone_exists': "⚠️ <b>Phone number already registered!</b>\n\nYou can login directly:\n{url}",
        'cancelled': "❌ Operation cancelled.",
        'creation_cancelled': "❌ Account creation cancelled.",
        'task_creation_cancelled': "❌ Task creation cancelled.",
        'no_tasks_today': "🎉 <b>No tasks scheduled for today!</b>\n\n📅 Date: {date}\n\nEnjoy your day! 🌟",
        'tasks_today': "📋 <b>Your tasks for today</b>\n📅 {date}\n\nYou have <b>{count}</b> scheduled tasks:\n\n",
        'have_a_good_day': "\n💪 Have a great day!",
        'create_task_start': "📝 <b>Create New Task</b>\n\n<b>Step 1/4:</b> Enter the task name\n\nSend /cancel to cancel",
        'task_name_short': "❌ Task name is too short. Enter a longer name:",
        'enter_task_desc': "📋 <b>Step 2/4:</b> Enter task description\n<i>(Optional - send \"skip\" to skip)</i>",
        'select_assistant': "🤖 <b>Step 3/4:</b> Select assistant\n\nChoose the assistant for this task:",
        'no_assistant': "No assistant ❌",
        'enter_task_time': "⏰ <b>Step {step}/4:</b> Enter task time\n\nEnter time in format: <code>YYYY-MM-DD HH:MM</code>\nExample: <code>{example_date}</code>\n\nOr send \"skip\" to create task without specific time",
        'invalid_time': "❌ Invalid time format.\n\nUse format: <code>YYYY-MM-DD HH:MM</code>\nExample: <code>{example_date}</code>\n\nRe-enter the time:",
        'time_error': "❌ Error processing time. Try again:",
        'confirm_task': "✅ <b>Confirm Task</b>\n\n📝 <b>Name:</b> {name}\n📋 <b>Description:</b> {desc}\n🤖 <b>Assistant:</b> {assistant}\n⏰ <b>Time:</b> {time}\n\nIs the data correct?\nSend <b>\"yes\"</b> to confirm or <b>\"no\"</b> to cancel",
        'task_created': "✅ <b>Task created successfully!</b>\n\n📝 <b>{name}</b>\n\n🔗 <a href=\"{link}\">Open task in browser</a>",
        'task_error': "❌ Error creating task: {error}",
        'error_checking_account': "❌ Error checking account",
        'not_specified': "Not specified",
        'not_available': "Not available",
        'skip': 'skip',
        'yes_values': ['yes', 'y', '1', 'نعم'],
    }
}


def get_user_lang(telegram_id: str) -> str:
    """Get user's preferred language from database"""
    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from app import app
        from models import User

        with app.app_context():
            user = User.query.filter_by(telegram_id=telegram_id).first()
            if user and user.language:
                return user.language.iso_code if hasattr(user.language, 'iso_code') else str(user.language)
    except Exception:
        pass
    return 'en'  # Default to English for non-logged in users


def get_msg(lang: str, key: str, **kwargs) -> str:
    """Get translated message"""
    messages = BOT_MESSAGES.get(lang, BOT_MESSAGES['en'])
    msg = messages.get(key, BOT_MESSAGES['en'].get(key, key))
    if kwargs:
        try:
            msg = msg.format(**kwargs)
        except KeyError:
            pass
    return msg


def get_example_date() -> str:
    """Get today's date + 1 hour as example"""
    cairo_tz = pytz.timezone('Africa/Cairo')
    now = datetime.now(cairo_tz)
    example = now.replace(hour=now.hour + 1 if now.hour < 23 else now.hour, minute=0)
    return example.strftime('%Y-%m-%d %H:%M')

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
    lang = get_user_lang(str(user.id))

    message = get_msg(lang, 'welcome', name=user.first_name)
    await update.message.reply_text(message, parse_mode='HTML')


async def show_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user their Telegram ID"""
    user = update.effective_user
    lang = get_user_lang(str(user.id))

    not_available = get_msg(lang, 'not_available')
    message = get_msg(lang, 'user_info',
        telegram_id=user.id,
        username=user.username if user.username else not_available,
        full_name=f"{user.first_name} {user.last_name or ''}".strip()
    )

    await update.message.reply_text(message, parse_mode='HTML')


async def today_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show today's scheduled tasks for the user"""
    telegram_user = update.effective_user
    telegram_id = str(telegram_user.id)
    lang = get_user_lang(telegram_id)

    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

        from app import app
        from models import db, User, Task
        from datetime import timedelta

        with app.app_context():
            user = User.query.filter_by(telegram_id=telegram_id).first()

            if not user:
                await update.message.reply_text(get_msg(lang, 'no_account'), parse_mode='HTML')
                return

            # Update lang based on user preference
            if user.language:
                lang = user.language.iso_code if hasattr(user.language, 'iso_code') else str(user.language)

            user_tz = pytz.timezone(user.timezone or 'Africa/Cairo')
            now_local = datetime.now(user_tz)
            today_start = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today_start + timedelta(days=1)

            today_start_utc = today_start.astimezone(pytz.UTC).replace(tzinfo=None)
            today_end_utc = today_end.astimezone(pytz.UTC).replace(tzinfo=None)

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
                    get_msg(lang, 'no_tasks_today', date=now_local.strftime('%Y-%m-%d')),
                    parse_mode='HTML'
                )
                return

            message = get_msg(lang, 'tasks_today', date=now_local.strftime('%Y-%m-%d'), count=len(tasks))

            for i, task in enumerate(tasks, 1):
                task_time_utc = pytz.UTC.localize(task.time)
                task_time_local = task_time_utc.astimezone(user_tz)
                time_str = task_time_local.strftime('%H:%M')
                status = "⏰" if task_time_local > now_local else "⚠️"

                message += f"{i}. {status} <b>{task.name}</b> ({time_str})\n"
                if task.description:
                    message += f"   📝 {task.description[:50]}{'...' if len(task.description) > 50 else ''}\n"

            message += get_msg(lang, 'have_a_good_day')
            await update.message.reply_text(message, parse_mode='HTML')

    except Exception as e:
        logger.error(f"Error fetching today's tasks: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}", parse_mode='HTML')


# ===== Create User Conversation =====

async def create_account_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start user creation process"""
    user = update.effective_user
    telegram_id = str(user.id)
    lang = get_user_lang(telegram_id)

    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from app import app
        from models import User

        with app.app_context():
            existing = User.query.filter_by(telegram_id=telegram_id).first()
            if existing:
                # Use existing user's language
                if existing.language:
                    lang = existing.language.iso_code if hasattr(existing.language, 'iso_code') else str(existing.language)
                await update.message.reply_text(
                    get_msg(lang, 'already_has_account', mobile=existing.mobile, url=SYSTEM_URL),
                    parse_mode='HTML'
                )
                return ConversationHandler.END
    except Exception as e:
        logger.warning(f"Could not check existing user: {e}")

    context.user_data['telegram_id'] = telegram_id
    context.user_data['telegram_username'] = user.username
    context.user_data['telegram_name'] = f"{user.first_name} {user.last_name or ''}".strip()
    context.user_data['lang'] = lang

    await update.message.reply_text(get_msg(lang, 'create_account_start'), parse_mode='HTML')
    return MOBILE


async def get_mobile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get mobile number"""
    lang = context.user_data.get('lang', 'en')
    mobile_input = update.message.text.strip()
    mobile = normalize_phone(mobile_input)

    if not re.match(r'^\d{10,15}$', mobile):
        await update.message.reply_text(get_msg(lang, 'invalid_phone'), parse_mode='HTML')
        return MOBILE

    context.user_data['mobile'] = mobile
    await update.message.reply_text(get_msg(lang, 'enter_email'), parse_mode='HTML')
    return EMAIL


async def get_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get email"""
    lang = context.user_data.get('lang', 'en')
    email_input = update.message.text.strip()

    if email_input.lower() in ['تخطي', 'skip', '-']:
        context.user_data['email'] = None
    else:
        if '@' not in email_input or '.' not in email_input:
            await update.message.reply_text(get_msg(lang, 'invalid_email'), parse_mode='HTML')
            return EMAIL
        context.user_data['email'] = email_input

    suggested_name = context.user_data.get('telegram_name', '')
    await update.message.reply_text(
        get_msg(lang, 'enter_name', telegram_name=suggested_name),
        parse_mode='HTML'
    )
    return NAME


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get name"""
    lang = context.user_data.get('lang', 'en')
    name_input = update.message.text.strip()

    if name_input.lower() in ['تخطي', 'skip', '-']:
        context.user_data['name'] = context.user_data.get('telegram_name')
    else:
        context.user_data['name'] = name_input

    # Show confirmation
    data = context.user_data
    not_specified = get_msg(lang, 'not_specified')

    message = get_msg(lang, 'confirm_data',
        mobile=data['mobile'],
        email=data.get('email') or not_specified,
        name=data.get('name') or not_specified,
        telegram_id=data['telegram_id']
    )

    await update.message.reply_text(message, parse_mode='HTML')
    return CONFIRM


async def confirm_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm and create user"""
    lang = context.user_data.get('lang', 'en')
    yes_values = BOT_MESSAGES.get(lang, BOT_MESSAGES['en']).get('yes_values', ['yes', 'y', '1'])
    response_text = update.message.text.strip().lower()

    if response_text not in yes_values:
        await update.message.reply_text(
            get_msg(lang, 'creation_cancelled'),
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    # Prepare data
    data = context.user_data
    user_data = {
        'mobile': data['mobile'],
        'telegram_id': data['telegram_id'],
        'email': data.get('email'),
        'name': data.get('name'),
        'lang': lang
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
                await update.message.reply_text(
                    get_msg(lang, 'account_created', url=SYSTEM_URL, mobile=data['mobile']),
                    parse_mode='HTML',
                    reply_markup=ReplyKeyboardRemove()
                )
            elif response.status_code == 409:
                await update.message.reply_text(
                    get_msg(lang, 'phone_exists', url=SYSTEM_URL),
                    parse_mode='HTML',
                    reply_markup=ReplyKeyboardRemove()
                )
            else:
                error = response.json().get('error', 'Unknown error')
                await update.message.reply_text(
                    f"❌ Error: {error}",
                    reply_markup=ReplyKeyboardRemove()
                )
        else:
            # No API key - create directly via database
            await create_account_directly(update, user_data, lang)

    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {e}")
        # Fallback to direct creation
        await create_account_directly(update, user_data, lang)
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        await update.message.reply_text(
            f"❌ Error: {str(e)}",
            reply_markup=ReplyKeyboardRemove()
        )

    return ConversationHandler.END


async def create_account_directly(update: Update, user_data: dict, lang: str = 'en'):
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
                    get_msg(lang, 'phone_exists', url=SYSTEM_URL),
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
                get_msg(lang, 'account_created', url=SYSTEM_URL, mobile=user_data['mobile']),
                parse_mode='HTML',
                reply_markup=ReplyKeyboardRemove()
            )

    except Exception as e:
        logger.error(f"Direct user creation failed: {e}")
        await update.message.reply_text(
            f"❌ Error: {str(e)}",
            reply_markup=ReplyKeyboardRemove()
        )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel current operation"""
    lang = context.user_data.get('lang', 'en')
    context.user_data.clear()
    await update.message.reply_text(
        get_msg(lang, 'cancelled'),
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


# ===== Create Task Conversation =====

async def create_task_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start task creation process"""
    telegram_user = update.effective_user
    telegram_id = str(telegram_user.id)
    lang = get_user_lang(telegram_id)

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
                    get_msg(lang, 'no_account'),
                    parse_mode='HTML'
                )
                return ConversationHandler.END

            # Update lang based on user preference
            if user.language:
                lang = user.language.iso_code if hasattr(user.language, 'iso_code') else str(user.language)

            # Store user info
            context.user_data['user_id'] = user.id
            context.user_data['user_name'] = user.name or user.mobile
            context.user_data['lang'] = lang

    except Exception as e:
        logger.error(f"Error checking user: {e}")
        await update.message.reply_text(get_msg(lang, 'error_checking_account'))
        return ConversationHandler.END

    await update.message.reply_text(get_msg(lang, 'create_task_start'), parse_mode='HTML')
    return TASK_NAME


async def get_task_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get task name"""
    lang = context.user_data.get('lang', 'en')
    task_name = update.message.text.strip()

    if len(task_name) < 2:
        await update.message.reply_text(get_msg(lang, 'task_name_short'))
        return TASK_NAME

    context.user_data['task_name'] = task_name
    await update.message.reply_text(get_msg(lang, 'enter_task_desc'), parse_mode='HTML')
    return TASK_DESC


async def get_task_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get task description"""
    lang = context.user_data.get('lang', 'en')
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
                example_date = get_example_date()
                await update.message.reply_text(
                    get_msg(lang, 'enter_task_time', step=3, example_date=example_date),
                    parse_mode='HTML'
                )
                return TASK_TIME

            # Build keyboard with assistants
            keyboard = []
            context.user_data['assistants'] = {}
            for assistant in assistants:
                context.user_data['assistants'][str(assistant.id)] = assistant.name
                keyboard.append([InlineKeyboardButton(assistant.name, callback_data=f"assistant_{assistant.id}")])

            keyboard.append([InlineKeyboardButton(get_msg(lang, 'no_assistant'), callback_data="assistant_none")])

            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                get_msg(lang, 'select_assistant'),
                parse_mode='HTML',
                reply_markup=reply_markup
            )
            return TASK_ASSISTANT

    except Exception as e:
        logger.error(f"Error getting assistants: {e}")
        context.user_data['task_assistant_id'] = None
        example_date = get_example_date()
        await update.message.reply_text(
            get_msg(lang, 'enter_task_time', step=3, example_date=example_date),
            parse_mode='HTML'
        )
        return TASK_TIME


async def select_assistant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle assistant selection callback"""
    query = update.callback_query
    await query.answer()

    lang = context.user_data.get('lang', 'en')
    data = query.data

    if data == "assistant_none":
        context.user_data['task_assistant_id'] = None
        context.user_data['task_assistant_name'] = get_msg(lang, 'no_assistant')
    else:
        assistant_id = data.replace("assistant_", "")
        context.user_data['task_assistant_id'] = int(assistant_id)
        context.user_data['task_assistant_name'] = context.user_data['assistants'].get(assistant_id, "Assistant")

    example_date = get_example_date()
    await query.edit_message_text(
        get_msg(lang, 'enter_task_time', step=4, example_date=example_date),
        parse_mode='HTML'
    )
    return TASK_TIME


async def get_task_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get task time"""
    lang = context.user_data.get('lang', 'en')
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
                example_date = get_example_date()
                await update.message.reply_text(
                    get_msg(lang, 'invalid_time', example_date=example_date),
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
            await update.message.reply_text(get_msg(lang, 'time_error'))
            return TASK_TIME

    # Show confirmation
    data = context.user_data
    not_specified = get_msg(lang, 'not_specified')
    no_assistant = get_msg(lang, 'no_assistant')

    message = get_msg(lang, 'confirm_task',
        name=data['task_name'],
        desc=data.get('task_desc') or not_specified,
        assistant=data.get('task_assistant_name', no_assistant),
        time=data.get('task_time_display') or not_specified
    )

    await update.message.reply_text(message, parse_mode='HTML')
    return TASK_CONFIRM


async def confirm_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm and create task"""
    lang = context.user_data.get('lang', 'en')
    yes_values = BOT_MESSAGES.get(lang, BOT_MESSAGES['en']).get('yes_values', ['yes', 'y', '1'])
    response_text = update.message.text.strip().lower()

    if response_text not in yes_values:
        await update.message.reply_text(
            get_msg(lang, 'task_creation_cancelled'),
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
                get_msg(lang, 'task_created', name=data['task_name'], link=task_link),
                parse_mode='HTML',
                reply_markup=ReplyKeyboardRemove()
            )

    except Exception as e:
        logger.error(f"Error creating task: {e}")
        await update.message.reply_text(
            get_msg(lang, 'task_error', error=str(e)),
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
