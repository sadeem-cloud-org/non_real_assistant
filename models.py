from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()


class User(db.Model):
    """User model for storing user information"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    telegram_id = db.Column(db.String(50), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    # Relationships
    otps = db.relationship('OTP', backref='user', lazy=True, cascade='all, delete-orphan')
    assistants = db.relationship('Assistant', backref='user', lazy=True, cascade='all, delete-orphan')
    tasks = db.relationship('Task', backref='user', lazy=True, cascade='all, delete-orphan')
    action_executions = db.relationship('ActionExecution', backref='user', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<User {self.phone}>'

    def update_last_login(self):
        """Update last login timestamp"""
        self.last_login = datetime.utcnow()
        db.session.commit()


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
    description = db.Column(db.Text)
    icon = db.Column(db.String(50), default='🤖')  # emoji or icon name
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    actions = db.relationship('Action', backref='assistant_type', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<AssistantType {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'display_name_ar': self.display_name_ar,
            'display_name_en': self.display_name_en,
            'description': self.description,
            'icon': self.icon,
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
    script_content = db.Column(db.Text)  # الكود نفسه
    trigger_type = db.Column(db.String(50), nullable=False)  # scheduled, manual, event_based
    trigger_config = db.Column(db.Text)  # JSON: {"cron": "0 8 * * *", "timezone": "Africa/Cairo"}
    output_format = db.Column(db.Text)  # JSON schema for expected output
    timeout = db.Column(db.Integer, default=60)  # seconds
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    executions = db.relationship('ActionExecution', backref='action', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Action {self.name}>'

    def get_trigger_config(self):
        """Get trigger config as dict"""
        if self.trigger_config:
            try:
                return json.loads(self.trigger_config)
            except:
                return {}
        return {}

    def set_trigger_config(self, config):
        """Set trigger config from dict"""
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
    script_id = db.Column(db.Integer, db.ForeignKey('scripts.id'))  # Link to script (for automation)
    name = db.Column(db.String(200))  # اسم مخصص من المستخدم
    is_enabled = db.Column(db.Boolean, default=True)
    settings = db.Column(db.Text)  # JSON - إعدادات خاصة بالمستخدم
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_run_at = db.Column(db.DateTime)

    # Relationships
    assistant_type = db.relationship('AssistantType', backref='user_assistants')
    linked_script = db.relationship('Script', backref='linked_to_assistant', foreign_keys=[script_id])
    tasks = db.relationship('Task', backref='assistant', lazy=True)

    def __repr__(self):
        return f'<Assistant {self.name or self.assistant_type.name} for user {self.user_id}>'

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

    def update_last_run(self):
        """Update last run timestamp"""
        self.last_run_at = datetime.utcnow()
        db.session.commit()

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'assistant_type': self.assistant_type.to_dict() if self.assistant_type else None,
            'script_id': self.script_id,
            'name': self.name,
            'is_enabled': self.is_enabled,
            'settings': self.get_settings(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_run_at': self.last_run_at.isoformat() if self.last_run_at else None
        }


class Task(db.Model):
    """Tasks created by users or assistants"""
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    assistant_id = db.Column(db.Integer, db.ForeignKey('assistants.id'))  # optional
    title = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text)
    priority = db.Column(db.String(20), default='medium')  # high, medium, low
    status = db.Column(db.String(20), default='new')  # new, in_progress, completed, cancelled
    due_date = db.Column(db.DateTime)
    reminder_time = db.Column(db.DateTime)
    tags = db.Column(db.Text)  # JSON array
    extra_data = db.Column(db.Text)  # JSON - additional data (renamed from metadata to avoid SQLAlchemy conflict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime)

    def __repr__(self):
        return f'<Task {self.title}>'

    def get_tags(self):
        """Get tags as list"""
        if self.tags:
            try:
                return json.loads(self.tags)
            except:
                return []
        return []

    def set_tags(self, tags_list):
        """Set tags from list"""
        self.tags = json.dumps(tags_list, ensure_ascii=False)

    def get_extra_data(self):
        """Get extra data as dict"""
        if self.extra_data:
            try:
                return json.loads(self.extra_data)
            except:
                return {}
        return {}

    def set_extra_data(self, data_dict):
        """Set extra data from dict"""
        self.extra_data = json.dumps(data_dict, ensure_ascii=False)

    def mark_completed(self):
        """Mark task as completed"""
        self.status = 'completed'
        self.completed_at = datetime.utcnow()
        db.session.commit()

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'assistant_id': self.assistant_id,
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
    assistant_id = db.Column(db.Integer, db.ForeignKey('assistants.id'))  # Optional link to assistant
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    language = db.Column(db.String(50), default='python')  # python, javascript, bash
    code = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    linked_assistant = db.relationship('Assistant', backref='owned_scripts', foreign_keys=[assistant_id])

    def __repr__(self):
        return f'<Script {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'description': self.description,
            'language': self.language,
            'code': self.code,
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

    # Relationships
    script = db.relationship('Script', backref='executions')

    def __repr__(self):
        return f'<ScriptExecution {self.id} - {self.status}>'

    def to_dict(self):
        return {
            'id': self.id,
            'script_id': self.script_id,
            'script_name': self.script.name if self.script else None,
            'script_language': self.script.language if self.script else None,
            'user_id': self.user_id,
            'status': self.status,
            'output': self.output,
            'error': self.error,
            'return_code': self.return_code,
            'execution_time': self.execution_time,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }


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

    def __repr__(self):
        return f'<ActionExecution {self.id} - {self.status}>'

    def get_input_data(self):
        """Get input data as dict"""
        if self.input_data:
            try:
                return json.loads(self.input_data)
            except:
                return {}
        return {}

    def set_input_data(self, data_dict):
        """Set input data from dict"""
        self.input_data = json.dumps(data_dict, ensure_ascii=False)

    def get_output_data(self):
        """Get output data as dict"""
        if self.output_data:
            try:
                return json.loads(self.output_data)
            except:
                return {}
        return {}

    def set_output_data(self, data_dict):
        """Set output data from dict"""
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
            'created_at': self.created_at.isoformat() if self.created_at else None
        }