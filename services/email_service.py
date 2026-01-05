"""Email Service for sending notifications"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from models import SystemSetting


class EmailService:
    """Handle sending emails via SMTP"""

    def __init__(self):
        self._config = None

    def _get_config(self):
        """Get email configuration from system settings"""
        if self._config is None:
            self._config = {
                'smtp_host': SystemSetting.get('email_smtp_host', 'smtp.gmail.com'),
                'smtp_port': SystemSetting.get('email_smtp_port', 587),
                'smtp_user': SystemSetting.get('email_smtp_user', ''),
                'smtp_password': SystemSetting.get('email_smtp_password', ''),
                'smtp_use_tls': SystemSetting.get('email_smtp_use_tls', True),
                'from_email': SystemSetting.get('email_from_address', ''),
                'from_name': SystemSetting.get('email_from_name', 'Non Real Assistant'),
            }
        return self._config

    def is_configured(self):
        """Check if email is properly configured"""
        config = self._get_config()
        return bool(config['smtp_user'] and config['smtp_password'] and config['from_email'])

    def send_email(self, to_email, subject, body_html, body_text=None, attachments=None):
        """
        Send an email

        Args:
            to_email: Recipient email address
            subject: Email subject
            body_html: HTML content of the email
            body_text: Plain text content (optional, will be derived from HTML if not provided)
            attachments: List of file paths to attach (optional)

        Returns:
            dict: {'success': bool, 'error': str or None}
        """
        if not self.is_configured():
            return {
                'success': False,
                'error': 'Email not configured. Please configure SMTP settings in system settings.'
            }

        config = self._get_config()

        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{config['from_name']} <{config['from_email']}>"
            msg['To'] = to_email

            # Add plain text part
            if body_text:
                part1 = MIMEText(body_text, 'plain', 'utf-8')
                msg.attach(part1)

            # Add HTML part
            part2 = MIMEText(body_html, 'html', 'utf-8')
            msg.attach(part2)

            # Add attachments
            if attachments:
                for file_path in attachments:
                    try:
                        with open(file_path, 'rb') as f:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(f.read())
                            encoders.encode_base64(part)
                            part.add_header(
                                'Content-Disposition',
                                f'attachment; filename="{file_path.split("/")[-1]}"'
                            )
                            msg.attach(part)
                    except Exception as e:
                        print(f"Failed to attach file {file_path}: {e}")

            # Connect and send
            if config['smtp_use_tls']:
                server = smtplib.SMTP(config['smtp_host'], config['smtp_port'])
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(config['smtp_host'], config['smtp_port'])

            server.login(config['smtp_user'], config['smtp_password'])
            server.sendmail(config['from_email'], to_email, msg.as_string())
            server.quit()

            return {'success': True, 'error': None}

        except smtplib.SMTPAuthenticationError as e:
            return {
                'success': False,
                'error': f'SMTP Authentication failed: {str(e)}'
            }
        except smtplib.SMTPException as e:
            return {
                'success': False,
                'error': f'SMTP Error: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to send email: {str(e)}'
            }

    def send_execution_result(self, user, script_name, status, output, error=None, share_url=None):
        """
        Send script execution result via email

        Args:
            user: User object with email
            script_name: Name of the script
            status: Execution status (success, failed, timeout)
            output: Script output
            error: Error message if any
            share_url: Public share URL if available
        """
        if not user.email or not user.notify_email:
            return {'success': False, 'error': 'User email not configured or notifications disabled'}

        # Determine status emoji and color
        status_config = {
            'success': {'emoji': '', 'color': '#10b981', 'text_ar': 'نجح', 'text_en': 'Success'},
            'failed': {'emoji': '', 'color': '#ef4444', 'text_ar': 'فشل', 'text_en': 'Failed'},
            'timeout': {'emoji': '', 'color': '#f59e0b', 'text_ar': 'انتهى الوقت', 'text_en': 'Timeout'},
            'running': {'emoji': '', 'color': '#3b82f6', 'text_ar': 'قيد التشغيل', 'text_en': 'Running'}
        }

        config = status_config.get(status, status_config['running'])
        lang = user.language or 'ar'

        # Build email content
        if lang == 'ar':
            subject = f"{config['emoji']} نتيجة تنفيذ: {script_name}"
            share_text = f'<p><a href="{share_url}">رابط المشاركة</a></p>' if share_url else ''
            body_html = f"""
            <html dir="rtl">
            <head><meta charset="utf-8"></head>
            <body style="font-family: Arial, sans-serif; direction: rtl;">
                <h2 style="color: {config['color']};">{config['emoji']} {config['text_ar']}</h2>
                <p><strong>السكريبت:</strong> {script_name}</p>
                <h3>الناتج:</h3>
                <pre style="background: #1e1e1e; color: #d4d4d4; padding: 15px; border-radius: 5px; direction: ltr; text-align: left; overflow-x: auto;">{output or 'لا يوجد ناتج'}</pre>
                {"<h3>الخطأ:</h3><pre style='background: #2d1f1f; color: #f48771; padding: 15px; border-radius: 5px; direction: ltr; text-align: left;'>" + error + "</pre>" if error else ""}
                {share_text}
                <hr>
                <p style="color: #666;">Non Real Assistant</p>
            </body>
            </html>
            """
        else:
            subject = f"{config['emoji']} Execution Result: {script_name}"
            share_text = f'<p><a href="{share_url}">Share Link</a></p>' if share_url else ''
            body_html = f"""
            <html>
            <head><meta charset="utf-8"></head>
            <body style="font-family: Arial, sans-serif;">
                <h2 style="color: {config['color']};">{config['emoji']} {config['text_en']}</h2>
                <p><strong>Script:</strong> {script_name}</p>
                <h3>Output:</h3>
                <pre style="background: #1e1e1e; color: #d4d4d4; padding: 15px; border-radius: 5px; overflow-x: auto;">{output or 'No output'}</pre>
                {"<h3>Error:</h3><pre style='background: #2d1f1f; color: #f48771; padding: 15px; border-radius: 5px;'>" + error + "</pre>" if error else ""}
                {share_text}
                <hr>
                <p style="color: #666;">Non Real Assistant</p>
            </body>
            </html>
            """

        return self.send_email(user.email, subject, body_html)


# Singleton instance
_email_service = None


def get_email_service():
    """Get email service singleton"""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
