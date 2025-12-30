"""Authentication service"""

import secrets
from datetime import datetime, timedelta
from models import db, User, OTP
from services.telegram_bot import TelegramOTPSender
from config import Config


class AuthService:
    """Handle authentication operations"""

    def __init__(self):
        self.telegram_sender = TelegramOTPSender()

    @staticmethod
    def generate_otp_code() -> str:
        """Generate a random 6-digit OTP code"""
        return ''.join([str(secrets.randbelow(10)) for _ in range(Config.OTP_LENGTH)])

    def request_otp(self, phone: str) -> dict:
        """
        Request OTP for a phone number
        Returns: dict with success status and message
        """
        user = User.query.filter_by(phone=phone).first()

        if not user:
            return {
                'success': False,
                'message': 'رقم الهاتف غير مسجل / Phone number not registered'
            }

        # Invalidate any existing unused OTPs for this user
        OTP.query.filter_by(user_id=user.id, used=False).update({'used': True})
        db.session.commit()

        # Generate new OTP
        otp_code = self.generate_otp_code()
        expires_at = datetime.utcnow() + timedelta(minutes=Config.OTP_EXPIRE_MINUTES)

        # Save OTP to database
        new_otp = OTP(
            user_id=user.id,
            code=otp_code,
            expires_at=expires_at
        )
        db.session.add(new_otp)
        db.session.commit()

        # Send OTP via Telegram
        result = self.telegram_sender.send_otp(user.telegram_id, otp_code)

        if result['success']:
            return {
                'success': True,
                'message': 'تم إرسال رمز التحقق إلى تيليجرام / OTP sent to Telegram'
            }
        else:
            # Delete the OTP since we couldn't send it
            db.session.delete(new_otp)
            db.session.commit()

            return {
                'success': False,
                'message': result['error'] if result.get('error') else 'فشل إرسال رمز التحقق / Failed to send OTP'
            }

    @staticmethod
    def verify_otp(phone: str, otp_code: str) -> dict:
        """
        Verify OTP code for a phone number
        Returns: dict with success status, message, and user data
        """
        user = User.query.filter_by(phone=phone).first()

        if not user:
            return {
                'success': False,
                'message': 'رقم الهاتف غير صحيح / Invalid phone number'
            }

        # Find valid OTP
        otp = OTP.query.filter_by(
            user_id=user.id,
            code=otp_code,
            used=False
        ).order_by(OTP.created_at.desc()).first()

        if not otp:
            return {
                'success': False,
                'message': 'رمز التحقق غير صحيح / Invalid OTP code'
            }

        if not otp.is_valid():
            return {
                'success': False,
                'message': 'رمز التحقق منتهي الصلاحية / OTP expired'
            }

        # Mark OTP as used
        otp.mark_as_used()

        # Update last login
        user.update_last_login()

        return {
            'success': True,
            'message': 'تم تسجيل الدخول بنجاح / Login successful',
            'user': {
                'id': user.id,
                'phone': user.phone
            }
        }
