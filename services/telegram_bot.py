"""Telegram Bot Service"""

import asyncio
import threading
from telegram import Bot
from telegram.error import TelegramError, Forbidden, BadRequest
from config import Config


class TelegramOTPSender:
    """Handle sending OTP via Telegram"""

    def __init__(self):
        self.bot_token = Config.TELEGRAM_BOT_TOKEN
        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN not set in environment variables")
        self.bot = Bot(token=self.bot_token)
        self._loop = None
        self._thread = None

    def _run_event_loop(self, loop):
        """Run event loop in separate thread"""
        asyncio.set_event_loop(loop)
        loop.run_forever()

    def _get_event_loop(self):
        """Get or create event loop"""
        if self._loop is None or self._loop.is_closed():
            self._loop = asyncio.new_event_loop()
            self._thread = threading.Thread(target=self._run_event_loop, args=(self._loop,), daemon=True)
            self._thread.start()
        return self._loop

    async def _send_otp_async(self, telegram_id: str, otp_code: str) -> dict:
        """Send OTP to user's Telegram (async)"""
        try:
            message = f"""
🔐 <b>Non Real Assistant - رمز التحقق</b>

رمز التحقق الخاص بك هو: <code>{otp_code}</code>

⏰ الرمز صالح لمدة {Config.OTP_EXPIRE_MINUTES} دقائق فقط.
⚠️ لا تشارك هذا الرمز مع أحد.

---
Your verification code is: <code>{otp_code}</code>

⏰ Valid for {Config.OTP_EXPIRE_MINUTES} minutes.
⚠️ Do not share this code with anyone.
            """

            await self.bot.send_message(
                chat_id=telegram_id,
                text=message.strip(),
                parse_mode='HTML'
            )
            return {'success': True, 'error': None}

        except Forbidden as e:
            error_msg = f"البوت محظور من المستخدم. الرجاء بدء محادثة مع البوت أولاً.\nBot is blocked by user. Please start a chat with the bot first."
            print(f"Telegram Forbidden Error for {telegram_id}: {e}")
            return {'success': False, 'error': error_msg}

        except BadRequest as e:
            if "chat not found" in str(e).lower():
                error_msg = f"لم يتم العثور على المحادثة. الرجاء بدء محادثة مع البوت أولاً عبر البحث عن اسم البوت في تيليجرام.\nChat not found. Please start a conversation with the bot first by searching for the bot name in Telegram."
            else:
                error_msg = f"خطأ في إرسال الرسالة: {str(e)}\nError sending message: {str(e)}"
            print(f"Telegram BadRequest Error for {telegram_id}: {e}")
            return {'success': False, 'error': error_msg}

        except TelegramError as e:
            error_msg = f"خطأ في Telegram: {str(e)}\nTelegram error: {str(e)}"
            print(f"Telegram Error for {telegram_id}: {e}")
            return {'success': False, 'error': error_msg}

        except Exception as e:
            error_msg = f"خطأ غير متوقع: {str(e)}\nUnexpected error: {str(e)}"
            print(f"Unexpected error sending OTP to {telegram_id}: {e}")
            return {'success': False, 'error': error_msg}

    def send_otp(self, telegram_id: str, otp_code: str) -> dict:
        """Send OTP to user's Telegram (sync wrapper)"""
        try:
            loop = self._get_event_loop()
            future = asyncio.run_coroutine_threadsafe(
                self._send_otp_async(telegram_id, otp_code),
                loop
            )
            result = future.result(timeout=10)
            return result
        except Exception as e:
            error_msg = f"خطأ في النظام: {str(e)}\nSystem error: {str(e)}"
            print(f"Error in send_otp wrapper: {e}")
            return {'success': False, 'error': error_msg}

    async def _send_message_async(self, telegram_id: str, message: str, parse_mode: str = 'HTML') -> dict:
        """Send a general message to user's Telegram (async)"""
        try:
            await self.bot.send_message(
                chat_id=telegram_id,
                text=message,
                parse_mode=parse_mode
            )
            return {'success': True, 'error': None}

        except Forbidden as e:
            error_msg = f"البوت محظور من المستخدم.\nBot is blocked by user."
            print(f"Telegram Forbidden Error for {telegram_id}: {e}")
            return {'success': False, 'error': error_msg}

        except BadRequest as e:
            error_msg = f"خطأ في إرسال الرسالة: {str(e)}\nError sending message: {str(e)}"
            print(f"Telegram BadRequest Error for {telegram_id}: {e}")
            return {'success': False, 'error': error_msg}

        except TelegramError as e:
            error_msg = f"خطأ في Telegram: {str(e)}\nTelegram error: {str(e)}"
            print(f"Telegram Error for {telegram_id}: {e}")
            return {'success': False, 'error': error_msg}

        except Exception as e:
            error_msg = f"خطأ غير متوقع: {str(e)}\nUnexpected error: {str(e)}"
            print(f"Unexpected error sending message to {telegram_id}: {e}")
            return {'success': False, 'error': error_msg}

    def send_message(self, telegram_id: str, message: str, parse_mode: str = 'HTML') -> dict:
        """Send a general message to user's Telegram (sync wrapper)"""
        try:
            loop = self._get_event_loop()
            future = asyncio.run_coroutine_threadsafe(
                self._send_message_async(telegram_id, message, parse_mode),
                loop
            )
            result = future.result(timeout=10)
            return result
        except Exception as e:
            error_msg = f"خطأ في النظام: {str(e)}\nSystem error: {str(e)}"
            print(f"Error in send_message wrapper: {e}")
            return {'success': False, 'error': error_msg}
