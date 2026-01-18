"""WAHA WhatsApp Service for sending notifications via WhatsApp"""

import requests
import logging
from models import WAHASession, db

logger = logging.getLogger(__name__)


class WAHAService:
    """Handle sending WhatsApp messages via WAHA API"""

    def __init__(self, session=None):
        self._session = session

    def _get_default_session(self):
        """Get the default WAHA session"""
        if self._session:
            return self._session
        return WAHASession.get_default()

    def is_configured(self):
        """Check if WAHA is properly configured"""
        session = self._get_default_session()
        return session is not None and session.is_active

    def get_session_status(self, session=None):
        """
        Get WAHA session status

        Returns:
            dict: {'success': bool, 'status': str, 'error': str or None}
        """
        session = session or self._get_default_session()
        if not session:
            return {'success': False, 'status': 'not_configured', 'error': 'No WAHA session configured'}

        try:
            headers = {}
            if session.api_key:
                headers['X-Api-Key'] = session.api_key

            response = requests.get(
                f"{session.api_url}/api/sessions/{session.session_name}",
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'status': data.get('status', 'unknown'),
                    'error': None,
                    'data': data
                }
            else:
                return {
                    'success': False,
                    'status': 'error',
                    'error': f'API returned status {response.status_code}'
                }

        except requests.exceptions.RequestException as e:
            logger.error(f"WAHA session status check failed: {e}")
            return {
                'success': False,
                'status': 'connection_error',
                'error': str(e)
            }

    def start_session(self, session=None):
        """
        Start a WAHA session

        Returns:
            dict: {'success': bool, 'qr': str or None, 'error': str or None}
        """
        session = session or self._get_default_session()
        if not session:
            return {'success': False, 'error': 'No WAHA session configured'}

        try:
            headers = {'Content-Type': 'application/json'}
            if session.api_key:
                headers['X-Api-Key'] = session.api_key

            payload = {
                'name': session.session_name,
                'start': True
            }

            response = requests.post(
                f"{session.api_url}/api/sessions/start",
                json=payload,
                headers=headers,
                timeout=30
            )

            if response.status_code in [200, 201]:
                data = response.json()
                return {
                    'success': True,
                    'data': data,
                    'error': None
                }
            else:
                return {
                    'success': False,
                    'error': f'Failed to start session: {response.text}'
                }

        except requests.exceptions.RequestException as e:
            logger.error(f"WAHA start session failed: {e}")
            return {'success': False, 'error': str(e)}

    def get_qr_code(self, session=None):
        """
        Get QR code for session authentication

        Returns:
            dict: {'success': bool, 'qr': str or None, 'error': str or None}
        """
        session = session or self._get_default_session()
        if not session:
            return {'success': False, 'error': 'No WAHA session configured'}

        try:
            headers = {}
            if session.api_key:
                headers['X-Api-Key'] = session.api_key

            response = requests.get(
                f"{session.api_url}/api/sessions/{session.session_name}/auth/qr",
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                # QR code is returned as image
                return {
                    'success': True,
                    'qr': response.content,
                    'content_type': response.headers.get('Content-Type', 'image/png'),
                    'error': None
                }
            else:
                return {
                    'success': False,
                    'qr': None,
                    'error': f'QR not available: {response.text}'
                }

        except requests.exceptions.RequestException as e:
            logger.error(f"WAHA get QR failed: {e}")
            return {'success': False, 'qr': None, 'error': str(e)}

    def send_message(self, phone_number, message, session=None):
        """
        Send a WhatsApp text message

        Args:
            phone_number: Phone number with country code (e.g., 201234567890)
            message: Text message to send
            session: Optional specific session to use

        Returns:
            dict: {'success': bool, 'message_id': str or None, 'error': str or None}
        """
        session = session or self._get_default_session()
        if not session:
            return {'success': False, 'error': 'No WAHA session configured'}

        if not session.is_active:
            return {'success': False, 'error': 'WAHA session is not active'}

        # Normalize phone number (remove + and spaces)
        phone = phone_number.replace('+', '').replace(' ', '').replace('-', '')

        # Format for WhatsApp (chatId format)
        chat_id = f"{phone}@c.us"

        try:
            headers = {'Content-Type': 'application/json'}
            if session.api_key:
                # WAHA uses X-Api-Key header for authentication
                headers['X-Api-Key'] = session.api_key

            payload = {
                'chatId': chat_id,
                'text': message,
                'session': session.session_name
            }

            logger.info(f"Sending WhatsApp message to {chat_id} via {session.api_url}")

            response = requests.post(
                f"{session.api_url}/api/sendText",
                json=payload,
                headers=headers,
                timeout=30
            )

            if response.status_code in [200, 201]:
                data = response.json()
                return {
                    'success': True,
                    'message_id': data.get('id'),
                    'error': None,
                    'data': data
                }
            else:
                error_msg = response.text
                try:
                    error_data = response.json()
                    error_msg = error_data.get('message', error_msg)
                except:
                    pass
                return {
                    'success': False,
                    'message_id': None,
                    'error': f'Failed to send message: {error_msg}'
                }

        except requests.exceptions.RequestException as e:
            logger.error(f"WAHA send message failed: {e}")
            return {
                'success': False,
                'message_id': None,
                'error': str(e)
            }

    def send_notification(self, user, title, message):
        """
        Send a notification to user via WhatsApp

        Args:
            user: User object with whatsapp_number field
            title: Notification title
            message: Notification message

        Returns:
            dict: {'success': bool, 'error': str or None}
        """
        if not user.whatsapp_number:
            return {'success': False, 'error': 'User has no WhatsApp number configured'}

        if not user.whatsapp_notify:
            return {'success': False, 'error': 'User has WhatsApp notifications disabled'}

        # Format message with title
        full_message = f"*{title}*\n\n{message}"

        return self.send_message(user.whatsapp_number, full_message)

    def send_task_reminder(self, user, task, system_url=''):
        """
        Send a task reminder via WhatsApp

        Args:
            user: User object
            task: Task object
            system_url: Base URL for task links

        Returns:
            dict: {'success': bool, 'error': str or None}
        """
        if not user.whatsapp_number or not user.whatsapp_notify:
            return {'success': False, 'error': 'WhatsApp not configured for user'}

        # Get user language
        lang = 'en'
        if user.language:
            lang = user.language.iso_code if hasattr(user.language, 'iso_code') else str(user.language)

        # Build message based on language
        if lang == 'ar':
            title = "تذكير بمهمة"
            message = f"""📋 *{task.name}*

"""
            if task.description:
                message += f"📝 {task.description}\n\n"
            if task.time:
                from datetime import datetime
                import pytz
                user_tz = pytz.timezone(user.timezone or 'Africa/Cairo')
                task_time_utc = pytz.UTC.localize(task.time)
                task_time_local = task_time_utc.astimezone(user_tz)
                message += f"⏰ الموعد: {task_time_local.strftime('%Y-%m-%d %H:%M')}\n\n"
            if system_url:
                message += f"🔗 {system_url}/tasks/{task.id}"
        else:
            title = "Task Reminder"
            message = f"""📋 *{task.name}*

"""
            if task.description:
                message += f"📝 {task.description}\n\n"
            if task.time:
                from datetime import datetime
                import pytz
                user_tz = pytz.timezone(user.timezone or 'Africa/Cairo')
                task_time_utc = pytz.UTC.localize(task.time)
                task_time_local = task_time_utc.astimezone(user_tz)
                message += f"⏰ Due: {task_time_local.strftime('%Y-%m-%d %H:%M')}\n\n"
            if system_url:
                message += f"🔗 {system_url}/tasks/{task.id}"

        full_message = f"*{title}*\n\n{message}"
        return self.send_message(user.whatsapp_number, full_message)

    def stop_session(self, session=None):
        """
        Stop a WAHA session

        Returns:
            dict: {'success': bool, 'error': str or None}
        """
        session = session or self._get_default_session()
        if not session:
            return {'success': False, 'error': 'No WAHA session configured'}

        try:
            headers = {'Content-Type': 'application/json'}
            if session.api_key:
                headers['X-Api-Key'] = session.api_key

            response = requests.post(
                f"{session.api_url}/api/sessions/{session.session_name}/stop",
                headers=headers,
                timeout=10
            )

            if response.status_code in [200, 201]:
                return {'success': True, 'error': None}
            else:
                return {'success': False, 'error': f'Failed to stop session: {response.text}'}

        except requests.exceptions.RequestException as e:
            logger.error(f"WAHA stop session failed: {e}")
            return {'success': False, 'error': str(e)}

    def logout_session(self, session=None):
        """
        Logout from a WAHA session (disconnect WhatsApp)

        Returns:
            dict: {'success': bool, 'error': str or None}
        """
        session = session or self._get_default_session()
        if not session:
            return {'success': False, 'error': 'No WAHA session configured'}

        try:
            headers = {'Content-Type': 'application/json'}
            if session.api_key:
                headers['X-Api-Key'] = session.api_key

            response = requests.post(
                f"{session.api_url}/api/sessions/{session.session_name}/logout",
                headers=headers,
                timeout=10
            )

            if response.status_code in [200, 201]:
                return {'success': True, 'error': None}
            else:
                return {'success': False, 'error': f'Failed to logout: {response.text}'}

        except requests.exceptions.RequestException as e:
            logger.error(f"WAHA logout failed: {e}")
            return {'success': False, 'error': str(e)}


# Singleton instance
_waha_service = None


def get_waha_service():
    """Get WAHA service singleton"""
    global _waha_service
    if _waha_service is None:
        _waha_service = WAHAService()
    return _waha_service
