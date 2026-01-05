import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Application configuration class"""

    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-me')
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')

    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///database.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Telegram
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

    # OTP
    OTP_EXPIRE_MINUTES = int(os.getenv('OTP_EXPIRE_MINUTES', 5))
    OTP_LENGTH = 6

    # Session
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours in seconds

    # External API Key for user creation
    API_SECRET_KEY = os.getenv('API_SECRET_KEY')
