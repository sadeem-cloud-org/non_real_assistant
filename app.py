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
app.config['BABEL_DEFAULT_LOCALE'] = 'ar'
app.config['BABEL_DEFAULT_TIMEZONE'] = 'Africa/Cairo'
app.config['LANGUAGES'] = {
    'ar': 'العربية',
    'en': 'English'
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
            return user.language

    # Fall back to browser preference
    return request.accept_languages.best_match(app.config['LANGUAGES'].keys()) or 'ar'


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

# Create tables
with app.app_context():
    db.create_all()

# Start background scheduler for reminders
from scheduler import start_scheduler
scheduler = start_scheduler(app)


@app.route('/favicon.ico')
def favicon():
    """Return empty favicon to prevent 404"""
    return '', 204


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
