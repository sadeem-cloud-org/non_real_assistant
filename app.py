"""
Non Real Assistant - Flask Application Entry Point
This is the main entry point for the application.
"""

from flask import Flask
from config import Config
from models import db
from routes import register_blueprints

# Create Flask app
app = Flask(__name__)
app.config.from_object(Config)

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
