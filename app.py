"""
Non Real Assistant - Flask Application Entry Point
This is the main entry point for the application.
"""

from flask import Flask, request, session
from flask_babel import Babel
from config import Config
from models import db
from routes import register_blueprints

# Create Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Configure Babel
app.config['BABEL_DEFAULT_LOCALE'] = 'en'  # Default to English
app.config['BABEL_DEFAULT_TIMEZONE'] = 'Africa/Cairo'
app.config['LANGUAGES'] = {
    'en': 'English',
    'ar': 'العربية'
}

# Initialize Babel
babel = Babel()


def get_locale():
    """Determine the best locale for the user"""
    # First check if user has set a language preference in session
    if 'language' in session:
        return session['language']

    # Then check if user is logged in and has a language preference
    if 'user_id' in session:
        from models import User
        user = User.query.get(session['user_id'])
        if user and user.language:
            return user.language.iso_code  # Return iso_code, not the Language object

    # Fall back to browser preference, default to English
    return request.accept_languages.best_match(app.config['LANGUAGES'].keys()) or 'en'


def get_timezone():
    """Determine the best timezone for the user"""
    if 'user_id' in session:
        from models import User
        user = User.query.get(session['user_id'])
        if user and user.timezone:
            return user.timezone
    return 'Africa/Cairo'


babel.init_app(app, locale_selector=get_locale, timezone_selector=get_timezone)

# Initialize database
db.init_app(app)

# Register all blueprints
register_blueprints(app)


# Validate session before each request
@app.before_request
def validate_session():
    """Clear session if user no longer exists in database"""
    if 'user_id' in session:
        from models import User
        user = User.query.get(session['user_id'])
        if not user:
            # User doesn't exist anymore, clear session
            session.clear()


# Context processor to make user data available in all templates
@app.context_processor
def inject_user():
    """Inject current user into all templates"""
    from models import User
    user = None
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
    return {'current_user': user}


# Translation filter for templates
@app.template_filter('trans')
def translate_filter(text):
    """Translate text using database translations"""
    from models import Language, Translation

    # Get current language
    lang_code = get_locale()
    language = Language.query.filter_by(iso_code=lang_code).first()

    if not language:
        return text

    # Look up translation
    trans = Translation.query.filter_by(
        language_id=language.id,
        key=text
    ).first()

    if trans and trans.value:
        return trans.value
    return text


# Make translation function available in templates
@app.context_processor
def inject_translate():
    """Inject translate function into all templates"""
    def translate(text):
        return translate_filter(text)
    return {'t': translate, 'translate': translate}


# Inject current language into templates
@app.context_processor
def inject_language():
    """Inject current language code into all templates"""
    lang = get_locale()
    return {
        'current_language': lang,
        'is_rtl': lang == 'ar'
    }


# Create tables and initialize default data
with app.app_context():
    db.create_all()

    # Create default languages if they don't exist
    from models import Language
    default_languages = [
        {'iso_code': 'en', 'name': 'English'},
        {'iso_code': 'ar', 'name': 'العربية'}
    ]

    for lang_data in default_languages:
        existing = Language.query.filter_by(iso_code=lang_data['iso_code']).first()
        if not existing:
            new_lang = Language(**lang_data)
            db.session.add(new_lang)
            print(f"✅ Created default language: {lang_data['name']}")

    db.session.commit()


@app.route('/favicon.ico')
def favicon():
    """Return empty favicon to prevent 404"""
    return '', 204


# Start scheduler for production (gunicorn) - only in first worker
import os
_scheduler_started = False

def start_scheduler_once():
    """Start scheduler only once (for first worker/thread)"""
    global _scheduler_started
    if not _scheduler_started:
        _scheduler_started = True
        from scheduler import start_scheduler
        start_scheduler(app)
        print("✅ Background scheduler started")

# Start scheduler on first request (works with gunicorn)
@app.before_request
def before_first_request():
    """Start scheduler on first request"""
    global _scheduler_started
    if not _scheduler_started:
        start_scheduler_once()


if __name__ == '__main__':
    # For development mode
    start_scheduler_once()
    app.run(debug=True, host='0.0.0.0', port=5000)
