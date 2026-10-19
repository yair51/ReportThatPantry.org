import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    DEBUG = False
    TESTING = False
    FLASK_APP = "main.py"
    SECRET_KEY = os.getenv("SECRET_KEY")  # No default; this should always be set externally
    SQLALCHEMY_DATABASE_URI = "postgresql" + os.getenv("DATABASE_URL")[8:]  # Include +psycopg2
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Google Maps API
    GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
     # Email (SMTP via Flask-Mail - Brevo by default, Mailtrap in development via .env)
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp-relay.brevo.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'False').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')  # Brevo SMTP login (e.g. 123abc@smtp-brevo.com), not your account email
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')  # Brevo SMTP key
    MAIL_DEFAULT_SENDER = ('Report That Pantry', os.environ.get('MAIL_DEFAULT_SENDER', 'info@reportthatpantry.org'))
    # File Uploads (S3)
    S3_BUCKET = os.environ.get('S3_BUCKET')
    S3_KEY = os.environ.get('S3_KEY')
    S3_SECRET = os.environ.get('S3_SECRET')
    S3_LOCATION = f'http://{S3_BUCKET}.s3.amazonaws.com/'
    # TODO - handle oversized uploads
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB upload limit (adjust as needed)


class ProductionConfig(Config):
    FLASK_ENV = 'production'
    DEBUG = False


class StagingConfig(Config):
    FLASK_ENV = 'staging'
    DEBUG = True


class DevelopmentConfig(Config):
    FLASK_ENV = 'development'
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///database.db")
