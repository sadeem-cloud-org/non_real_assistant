from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
import secrets

db = SQLAlchemy()


class User(db.Model):
    """User model for storing user information"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    telegram_id = db.Column(db.String(50), unique=True, nullable=False)

    # New fields for user profile
    name = db.Column(db.String(100))
    email = db.Column(db.String(200))
    language = db.Column(db.String(10), default='ar')  # ar, en
    timezone = db.Column(db.String(50), default='Africa/Cairo')

    # Notification preferences
    notify_telegram = db.Column(db.Boolean, default=True)
    notify_email = db.Column(db.Boolean, default=False)
    notify_browser = db.Column(db.Boolean, default=True)

    # User settings (JSON)
    settings = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    # Relationships
    otps = db.relationship('OTP', backref='user', lazy=True, cascade='all, delete-orphan')
    assistants = db.relationship('Assistant', backref='user', lazy=True, cascade='all, delete-orphan')
    tasks = db.relationship('Task', backref='user', lazy=True, cascade='all, delete-orphan')
    scripts = db.relationship('Script', backref='user', lazy=True, cascade='all, delete-orphan')
    action_executions = db.relationship('ActionExecution', backref='user', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<User {self.phone}>'

    def get_settings(self):
        """Get settings as dict"""
        if self.settings:
            try:
                return json.loads(self.settings)
            except:
                return {}
        return {}

    def set_settings(self, settings_dict):
        """Set settings from dict"""
        self.settings = json.dumps(settings_dict, ensure_ascii=False)

    def update_last_login(self):
        """Update last login timestamp"""
        self.last_login = datetime.utcnow()
        db.session.commit()

    def to_dict(self):
        return {
            'id': self.id,
            'phone': self.phone,
            'telegram_id': self.telegram_id,
            'name': self.name,
            'email': self.email,
            'language': self.language,
            'timezone': self.timezone,
            'notify_telegram': self.notify_telegram,
            'notify_email': self.notify_email,
            'notify_browser': self.notify_browser,
            'settings': self.get_settings(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }


class SystemSettings(db.Model):
    """System-wide settings"""
    __tablename__ = 'system_settings'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    value_type = db.Column(db.String(20), default='string')  # string, json, int, bool
    description = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<SystemSettings {self.key}>'

    def get_value(self):
        """Get typed value"""
        if self.value is None:
            return None
        if self.value_type == 'json':
            try:
                return json.loads(self.value)
            except:
                return {}
        elif self.value_type == 'int':
            return int(self.value)
        elif self.value_type == 'bool':
            return self.value.lower() in ('true', '1', 'yes')
        return self.value

    def set_value(self, val):
        """Set value with type handling"""
        if self.value_type == 'json':
            self.value = json.dumps(val, ensure_ascii=False)
        else:
            self.value = str(val)

    @staticmethod
    def get(key, default=None):
        """Get setting value by key"""
        setting = SystemSettings.query.filter_by(key=key).first()
        if setting:
            return setting.get_value()
        return default

    @staticmethod
    def set(key, value, value_type='string', description=None):
        """Set setting value"""
        setting = SystemSettings.query.filter_by(key=key).first()
        if not setting:
            setting = SystemSettings(key=key, value_type=value_type, description=description)
            db.session.add(setting)
        setting.set_value(value)
        db.session.commit()
        return setting


class OTP(db.Model):
    """OTP model for storing one-time passwords"""
    __tablename__ = 'otps'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    code = db.Column(db.String(6), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<OTP {self.code} for user {self.user_id}>'

    def is_valid(self):
        """Check if OTP is valid (not used and not expired)"""
        return not self.used and datetime.utcnow() < self.expires_at

    def mark_as_used(self):
        """Mark OTP as used"""
        self.used = True
        db.session.commit()


class AssistantType(db.Model):
    """Types of assistants available"""
    __tablename__ = 'assistant_types'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)  # reminder, server_monitor, etc.
    display_name_ar = db.Column(db.String(100), nullable=False)
    display_name_en = db.Column(db.String(100), nullable=False)
    description_ar = db.Column(db.Text)
    description_en = db.Column(db.Text)
    icon = db.Column(db.String(50), default='ti-robot')  # Tabler icon name
    color = db.Column(db.String(20), default='blue')  # Tabler color
    default_settings = db.Column(db.Text)  # JSON - default settings for this type
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    actions = db.relationship('Action', backref='assistant_type', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<AssistantType {self.name}>'

    def get_default_settings(self):
        if self.default_settings:
            try:
                return json.loads(self.default_settings)
            except:
                return {}
        return {}

    def to_dict(self, lang='ar'):
        return {
            'id': self.id,
            'name': self.name,
            'display_name': self.display_name_ar if lang == 'ar' else self.display_name_en,
            'display_name_ar': self.display_name_ar,
            'display_name_en': self.display_name_en,
            'description': self.description_ar if lang == 'ar' else self.description_en,
            'icon': self.icon,
            'color': self.color,
            'is_active': self.is_active,
            'actions_count': len(self.actions)
        }


class Action(db.Model):
    """Actions that can be performed by assistants"""
    __tablename__ = 'actions'

    id = db.Column(db.Integer, primary_key=True)
    assistant_type_id = db.Column(db.Integer, db.ForeignKey('assistant_types.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    display_name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    execution_type = db.Column(db.String(50), nullable=False)  # python_script, bash_command, api_call
    script_content = db.Column(db.Text)
    trigger_type = db.Column(db.String(50), nullable=False)  # scheduled, manual, event_based
    trigger_config = db.Column(db.Text)  # JSON
    output_format = db.Column(db.Text)  # JSON schema
    timeout = db.Column(db.Integer, default=60)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    executions = db.relationship('ActionExecution', backref='action', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Action {self.name}>'

    def get_trigger_config(self):
        if self.trigger_config:
            try:
                return json.loads(self.trigger_config)
            except:
                return {}
        return {}

    def set_trigger_config(self, config):
        self.trigger_config = json.dumps(config, ensure_ascii=False)

    def to_dict(self):
        return {
            'id': self.id,
            'assistant_type_id': self.assistant_type_id,
            'name': self.name,
            'display_name': self.display_name,
            'description': self.description,
            'execution_type': self.execution_type,
            'trigger_type': self.trigger_type,
            'trigger_config': self.get_trigger_config(),
            'timeout': self.timeout,
            'is_active': self.is_active
        }


class Assistant(db.Model):
    """User's active assistants"""
    __tablename__ = 'assistants'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    assistant_type_id = db.Column(db.Integer, db.ForeignKey('assistant_types.id'), nullable=False)
    script_id = db.Column(db.Integer, db.ForeignKey('scripts.id'))
    name = db.Column(db.String(200))
    description = db.Column(db.Text)
    is_enabled = db.Column(db.Boolean, default=True)
    settings = db.Column(db.Text)  # JSON
    schedule = db.Column(db.Text)  # JSON - cron schedule

    # Notification settings for this assistant
    send_to_telegram = db.Column(db.Boolean, default=True)
    send_to_email = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_run_at = db.Column(db.DateTime)

    # Relationships
    assistant_type = db.relationship('AssistantType', backref='user_assistants')
    linked_script = db.relationship('Script', backref='linked_to_assistant', foreign_keys=[script_id])
    tasks = db.relationship('Task', backref='assistant', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Assistant {self.name or "Unnamed"} for user {self.user_id}>'

    def get_settings(self):
        if self.settings:
            try:
                return json.loads(self.settings)
            except:
                return {}
        return {}

    def set_settings(self, settings_dict):
        self.settings = json.dumps(settings_dict, ensure_ascii=False)

    def get_schedule(self):
        if self.schedule:
            try:
                return json.loads(self.schedule)
            except:
                return {}
        return {}

    def set_schedule(self, schedule_dict):
        self.schedule = json.dumps(schedule_dict, ensure_ascii=False)

    def update_last_run(self):
        self.last_run_at = datetime.utcnow()
        db.session.commit()

    def to_dict(self, lang='ar'):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'assistant_type': self.assistant_type.to_dict(lang) if self.assistant_type else None,
            'script_id': self.script_id,
            'name': self.name,
            'description': self.description,
            'is_enabled': self.is_enabled,
            'settings': self.get_settings(),
            'schedule': self.get_schedule(),
            'send_to_telegram': self.send_to_telegram,
            'send_to_email': self.send_to_email,
            'tasks_count': len(self.tasks) if self.tasks else 0,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_run_at': self.last_run_at.isoformat() if self.last_run_at else None
        }


class Task(db.Model):
    """Tasks created by users or assistants"""
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    assistant_id = db.Column(db.Integer, db.ForeignKey('assistants.id'))
    title = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text)
    priority = db.Column(db.String(20), default='medium')  # high, medium, low
    status = db.Column(db.String(20), default='new')  # new, in_progress, completed, cancelled
    due_date = db.Column(db.DateTime)
    reminder_time = db.Column(db.DateTime)
    tags = db.Column(db.Text)  # JSON array
    extra_data = db.Column(db.Text)  # JSON
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime)

    def __repr__(self):
        return f'<Task {self.title}>'

    def get_tags(self):
        if self.tags:
            try:
                return json.loads(self.tags)
            except:
                return []
        return []

    def set_tags(self, tags_list):
        self.tags = json.dumps(tags_list, ensure_ascii=False)

    def get_extra_data(self):
        if self.extra_data:
            try:
                return json.loads(self.extra_data)
            except:
                return {}
        return {}

    def set_extra_data(self, data_dict):
        self.extra_data = json.dumps(data_dict, ensure_ascii=False)

    def mark_completed(self):
        self.status = 'completed'
        self.completed_at = datetime.utcnow()
        db.session.commit()

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'assistant_id': self.assistant_id,
            'assistant_name': self.assistant.name if self.assistant else None,
            'title': self.title,
            'description': self.description,
            'priority': self.priority,
            'status': self.status,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'reminder_time': self.reminder_time.isoformat() if self.reminder_time else None,
            'tags': self.get_tags(),
            'extra_data': self.get_extra_data(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }


class Script(db.Model):
    """Scripts written by users"""
    __tablename__ = 'scripts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    assistant_id = db.Column(db.Integer, db.ForeignKey('assistants.id'))
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    language = db.Column(db.String(50), default='python')  # python, javascript, bash
    code = db.Column(db.Text, nullable=False)

    # Output notification settings
    send_output_telegram = db.Column(db.Boolean, default=False)
    send_output_email = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    linked_assistant = db.relationship('Assistant', backref='owned_scripts', foreign_keys=[assistant_id])
    executions = db.relationship('ScriptExecution', backref='script', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Script {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'assistant_id': self.assistant_id,
            'name': self.name,
            'description': self.description,
            'language': self.language,
            'code': self.code,
            'send_output_telegram': self.send_output_telegram,
            'send_output_email': self.send_output_email,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class ScriptExecution(db.Model):
    """Log of script executions"""
    __tablename__ = 'script_executions'

    id = db.Column(db.Integer, primary_key=True)
    script_id = db.Column(db.Integer, db.ForeignKey('scripts.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), default='running')  # running, success, failed, timeout
    output = db.Column(db.Text)  # stdout
    error = db.Column(db.Text)  # stderr
    return_code = db.Column(db.Integer)
    execution_time = db.Column(db.Float)  # seconds
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)

    # Public sharing
    share_token = db.Column(db.String(64), unique=True)
    is_public = db.Column(db.Boolean, default=False)

    # Notification sent flags
    telegram_sent = db.Column(db.Boolean, default=False)
    email_sent = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<ScriptExecution {self.id} - {self.status}>'

    def generate_share_token(self):
        """Generate a unique share token"""
        self.share_token = secrets.token_urlsafe(32)
        self.is_public = True
        return self.share_token

    def get_share_url(self, base_url=''):
        """Get the public share URL"""
        if self.share_token:
            return f"{base_url}/share/execution/{self.share_token}"
        return None

    def to_dict(self, include_output=True):
        result = {
            'id': self.id,
            'script_id': self.script_id,
            'script_name': self.script.name if self.script else None,
            'script_language': self.script.language if self.script else None,
            'user_id': self.user_id,
            'status': self.status,
            'return_code': self.return_code,
            'execution_time': self.execution_time,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'is_public': self.is_public,
            'share_token': self.share_token if self.is_public else None
        }
        if include_output:
            result['output'] = self.output
            result['error'] = self.error
        return result


class ActionExecution(db.Model):
    """Log of action executions"""
    __tablename__ = 'action_executions'

    id = db.Column(db.Integer, primary_key=True)
    action_id = db.Column(db.Integer, db.ForeignKey('actions.id'), nullable=False)
    assistant_id = db.Column(db.Integer, db.ForeignKey('assistants.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, running, success, failed
    input_data = db.Column(db.Text)  # JSON
    output_data = db.Column(db.Text)  # JSON
    error_message = db.Column(db.Text)
    execution_time = db.Column(db.Float)  # seconds
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Public sharing
    share_token = db.Column(db.String(64), unique=True)
    is_public = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<ActionExecution {self.id} - {self.status}>'

    def generate_share_token(self):
        self.share_token = secrets.token_urlsafe(32)
        self.is_public = True
        return self.share_token

    def get_input_data(self):
        if self.input_data:
            try:
                return json.loads(self.input_data)
            except:
                return {}
        return {}

    def set_input_data(self, data_dict):
        self.input_data = json.dumps(data_dict, ensure_ascii=False)

    def get_output_data(self):
        if self.output_data:
            try:
                return json.loads(self.output_data)
            except:
                return {}
        return {}

    def set_output_data(self, data_dict):
        self.output_data = json.dumps(data_dict, ensure_ascii=False)

    def to_dict(self):
        return {
            'id': self.id,
            'action_id': self.action_id,
            'assistant_id': self.assistant_id,
            'user_id': self.user_id,
            'status': self.status,
            'input_data': self.get_input_data(),
            'output_data': self.get_output_data(),
            'error_message': self.error_message,
            'execution_time': self.execution_time,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_public': self.is_public,
            'share_token': self.share_token if self.is_public else None
        }
