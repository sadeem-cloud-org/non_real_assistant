from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
import secrets

db = SQLAlchemy()


# ===== Language Table =====

class Language(db.Model):
    """Languages for UI translations"""
    __tablename__ = 'languages'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # العربية, English
    iso_code = db.Column(db.String(10), unique=True, nullable=False)  # ar, en
    create_time = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    translations = db.relationship('Translation', backref='language', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Language {self.iso_code}>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'iso_code': self.iso_code
        }


class Translation(db.Model):
    """UI translations"""
    __tablename__ = 'translations'

    id = db.Column(db.Integer, primary_key=True)
    language_id = db.Column(db.Integer, db.ForeignKey('languages.id'), nullable=False)
    key = db.Column(db.String(500), nullable=False)  # Original text or unique key
    value = db.Column(db.Text)  # Translated text
    context = db.Column(db.String(200))  # File or context where it's used
    create_time = db.Column(db.DateTime, default=datetime.utcnow)
    update_time = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('language_id', 'key', name='unique_translation'),
    )

    def __repr__(self):
        return f'<Translation {self.key[:30]}... ({self.language.iso_code if self.language else "?"})>'

    def to_dict(self):
        return {
            'id': self.id,
            'language_id': self.language_id,
            'language_code': self.language.iso_code if self.language else None,
            'key': self.key,
            'value': self.value,
            'context': self.context,
            'create_time': self.create_time.isoformat() if self.create_time else None,
            'update_time': self.update_time.isoformat() if self.update_time else None
        }


# ===== System Settings =====

class SystemSetting(db.Model):
    """System-wide settings"""
    __tablename__ = 'system_settings'

    id = db.Column(db.Integer, primary_key=True)
    telegram_bot_token = db.Column(db.String(200))
    otp_expiration_seconds = db.Column(db.Integer, default=300)  # 5 minutes
    default_language_id = db.Column(db.Integer, db.ForeignKey('languages.id'))
    title = db.Column(db.String(200), default='Non Real Assistant')
    logo = db.Column(db.LargeBinary)

    # Relationships
    default_language = db.relationship('Language')

    def __repr__(self):
        return f'<SystemSetting {self.id}>'

    @staticmethod
    def get_settings():
        """Get or create system settings"""
        settings = SystemSetting.query.first()
        if not settings:
            settings = SystemSetting()
            db.session.add(settings)
            db.session.commit()
        return settings

    def to_dict(self):
        return {
            'id': self.id,
            'telegram_bot_token': self.telegram_bot_token,
            'otp_expiration_seconds': self.otp_expiration_seconds,
            'default_language_id': self.default_language_id,
            'title': self.title,
            'has_logo': self.logo is not None
        }

    @staticmethod
    def get(key, default=None):
        """Get a key-value setting"""
        setting = KeyValueSetting.query.filter_by(key=key).first()
        if setting:
            return setting.get_value()
        return default

    @staticmethod
    def set(key, value):
        """Set a key-value setting"""
        setting = KeyValueSetting.query.filter_by(key=key).first()
        if setting:
            setting.set_value(value)
        else:
            setting = KeyValueSetting(key=key)
            setting.set_value(value)
            db.session.add(setting)
        db.session.commit()
        return setting


class KeyValueSetting(db.Model):
    """Key-value settings storage"""
    __tablename__ = 'key_value_settings'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    value_type = db.Column(db.String(20), default='string')  # string, int, bool, json

    def get_value(self):
        """Get value with proper type conversion"""
        if self.value is None:
            return None
        if self.value_type == 'int':
            return int(self.value)
        elif self.value_type == 'bool':
            return self.value.lower() in ('true', '1', 'yes')
        elif self.value_type == 'json':
            return json.loads(self.value)
        return self.value

    def set_value(self, value):
        """Set value with type detection"""
        if isinstance(value, bool):
            self.value_type = 'bool'
            self.value = 'true' if value else 'false'
        elif isinstance(value, int):
            self.value_type = 'int'
            self.value = str(value)
        elif isinstance(value, (dict, list)):
            self.value_type = 'json'
            self.value = json.dumps(value)
        else:
            self.value_type = 'string'
            self.value = str(value) if value is not None else None


# ===== User & Auth =====

class User(db.Model):
    """User model"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    mobile = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100))
    telegram_id = db.Column(db.String(50), unique=True)
    email = db.Column(db.String(200))
    timezone = db.Column(db.String(50), default='Africa/Cairo')
    language_id = db.Column(db.Integer, db.ForeignKey('languages.id'))
    browser_notify = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    create_time = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    language = db.relationship('Language')
    otps = db.relationship('OTP', backref='user', lazy=True, cascade='all, delete-orphan')
    login_history = db.relationship('UserLoginHistory', backref='user', lazy=True, cascade='all, delete-orphan')
    assistants = db.relationship('Assistant', backref='user', lazy=True, cascade='all, delete-orphan')
    tasks = db.relationship('Task', backref='user', lazy=True, cascade='all, delete-orphan')
    scripts = db.relationship('Script', backref='user', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<User {self.mobile}>'

    def to_dict(self):
        return {
            'id': self.id,
            'mobile': self.mobile,
            'name': self.name,
            'telegram_id': self.telegram_id,
            'email': self.email,
            'timezone': self.timezone,
            'language_id': self.language_id,
            'language': self.language.to_dict() if self.language else None,
            'browser_notify': self.browser_notify,
            'is_admin': self.is_admin,
            'create_time': self.create_time.isoformat() if self.create_time else None
        }


class UserLoginHistory(db.Model):
    """Track user login history"""
    __tablename__ = 'user_login_history'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    ip = db.Column(db.String(50))
    browser = db.Column(db.String(200))
    create_time = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<UserLoginHistory {self.user_id} - {self.ip}>'

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'ip': self.ip,
            'browser': self.browser,
            'create_time': self.create_time.isoformat() if self.create_time else None
        }


class OTP(db.Model):
    """OTP model for one-time passwords"""
    __tablename__ = 'otps'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    code = db.Column(db.String(6), nullable=False)
    create_time = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<OTP {self.code} for user {self.user_id}>'

    def is_valid(self):
        """Check if OTP is valid"""
        return not self.used and datetime.utcnow() < self.expires_at

    def mark_as_used(self):
        """Mark OTP as used"""
        self.used = True
        db.session.commit()


# ===== Notification Templates =====

class NotifyTemplate(db.Model):
    """Notification message templates"""
    __tablename__ = 'notify_templates'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    text = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f'<NotifyTemplate {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'text': self.text
        }

    def render(self, **kwargs):
        """Render template with variables"""
        try:
            return self.text.format(**kwargs)
        except:
            return self.text


# ===== Assistant Types =====

class AssistantType(db.Model):
    """Types of assistants"""
    __tablename__ = 'assistant_types'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    create_time = db.Column(db.DateTime, default=datetime.utcnow)
    related_action = db.Column(db.String(20), default='task')  # 'task' or 'script'

    # Relationships
    assistants = db.relationship('Assistant', backref='assistant_type', lazy=True)

    def __repr__(self):
        return f'<AssistantType {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'related_action': self.related_action,
            'create_time': self.create_time.isoformat() if self.create_time else None
        }


# ===== Assistants =====

class Assistant(db.Model):
    """User's assistants"""
    __tablename__ = 'assistants'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    create_time = db.Column(db.DateTime, default=datetime.utcnow)
    assistant_type_id = db.Column(db.Integer, db.ForeignKey('assistant_types.id'), nullable=False)
    create_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Notification settings
    telegram_notify = db.Column(db.Boolean, default=True)
    email_notify = db.Column(db.Boolean, default=False)
    notify_template_id = db.Column(db.Integer, db.ForeignKey('notify_templates.id'))

    # Scheduling
    run_every = db.Column(db.String(20))  # minute, hour, day, week, month
    next_run_time = db.Column(db.DateTime)

    # Relationships
    notify_template = db.relationship('NotifyTemplate')
    tasks = db.relationship('Task', backref='assistant', lazy=True, cascade='all, delete-orphan')
    scripts = db.relationship('Script', backref='assistant', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Assistant {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'create_time': self.create_time.isoformat() if self.create_time else None,
            'assistant_type_id': self.assistant_type_id,
            'assistant_type': self.assistant_type.to_dict() if self.assistant_type else None,
            'create_user_id': self.create_user_id,
            'telegram_notify': self.telegram_notify,
            'email_notify': self.email_notify,
            'notify_template_id': self.notify_template_id,
            'notify_template': self.notify_template.to_dict() if self.notify_template else None,
            'run_every': self.run_every,
            'next_run_time': self.next_run_time.isoformat() if self.next_run_time else None,
            'tasks_count': len(self.tasks) if self.tasks else 0,
            'scripts_count': len(self.scripts) if self.scripts else 0
        }


# ===== Tasks =====

class Task(db.Model):
    """Tasks for task-type assistants"""
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(500), nullable=False)
    create_time = db.Column(db.DateTime, default=datetime.utcnow)
    create_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    description = db.Column(db.Text)
    time = db.Column(db.DateTime)  # Due/reminder time
    complete_time = db.Column(db.DateTime)
    cancel_time = db.Column(db.DateTime)
    assistant_id = db.Column(db.Integer, db.ForeignKey('assistants.id'))
    notify_sent = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<Task {self.name}>'

    def get_status(self):
        """Get task status based on times"""
        if self.cancel_time:
            return 'cancelled'
        if self.complete_time:
            return 'completed'
        if self.time and datetime.utcnow() > self.time:
            return 'overdue'
        return 'pending'

    def mark_completed(self):
        """Mark task as completed"""
        self.complete_time = datetime.utcnow()
        db.session.commit()

    def mark_cancelled(self):
        """Mark task as cancelled"""
        self.cancel_time = datetime.utcnow()
        db.session.commit()

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'create_time': self.create_time.isoformat() if self.create_time else None,
            'create_user_id': self.create_user_id,
            'description': self.description,
            'time': self.time.isoformat() if self.time else None,
            'status': self.get_status(),
            'complete_time': self.complete_time.isoformat() if self.complete_time else None,
            'cancel_time': self.cancel_time.isoformat() if self.cancel_time else None,
            'assistant_id': self.assistant_id,
            'assistant_name': self.assistant.name if self.assistant else None,
            'notify_sent': self.notify_sent
        }


# ===== Scripts =====

class Script(db.Model):
    """Scripts for script-type assistants"""
    __tablename__ = 'scripts'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    code = db.Column(db.Text, nullable=False)
    create_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    create_time = db.Column(db.DateTime, default=datetime.utcnow)
    notify_template_id = db.Column(db.Integer, db.ForeignKey('notify_templates.id'))
    assistant_id = db.Column(db.Integer, db.ForeignKey('assistants.id'))

    # Relationships
    notify_template = db.relationship('NotifyTemplate')
    executions = db.relationship('ScriptExecuteLog', backref='script', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Script {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'create_user_id': self.create_user_id,
            'create_time': self.create_time.isoformat() if self.create_time else None,
            'notify_template_id': self.notify_template_id,
            'notify_template': self.notify_template.to_dict() if self.notify_template else None,
            'assistant_id': self.assistant_id,
            'assistant_name': self.assistant.name if self.assistant else None
        }


# ===== Script Execution Log =====

class ScriptExecuteLog(db.Model):
    """Log of script executions"""
    __tablename__ = 'script_execute_logs'

    id = db.Column(db.Integer, primary_key=True)
    script_id = db.Column(db.Integer, db.ForeignKey('scripts.id'), nullable=False)
    create_time = db.Column(db.DateTime, default=datetime.utcnow)
    input = db.Column(db.Text)
    output = db.Column(db.Text)
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    state = db.Column(db.String(20), default='pending')  # pending, running, success, failed

    # Public sharing
    share_token = db.Column(db.String(64), unique=True)
    is_public = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<ScriptExecuteLog {self.id} - {self.state}>'

    def get_execution_time(self):
        """Calculate execution time in seconds"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    def generate_share_token(self):
        """Generate a unique share token"""
        self.share_token = secrets.token_urlsafe(32)
        self.is_public = True
        return self.share_token

    def to_dict(self, include_output=True):
        result = {
            'id': self.id,
            'script_id': self.script_id,
            'script_name': self.script.name if self.script else None,
            'create_time': self.create_time.isoformat() if self.create_time else None,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'state': self.state,
            'execution_time': self.get_execution_time(),
            'is_public': self.is_public,
            'share_token': self.share_token if self.is_public else None
        }
        if include_output:
            result['input'] = self.input
            result['output'] = self.output
        return result
