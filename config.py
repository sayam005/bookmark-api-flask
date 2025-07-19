import os
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_mail import Mail

# Load environment variables from .env file
load_dotenv()

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
mail = Mail()

class Config:
    """Base configuration."""
    SECRET_KEY = os.getenv('SECRET_KEY', 'a_default_secret_key_for_development')
    SQLALCHEMY_TRACK_MODIFICATIONS = os.environ.get('SQLALCHEMY_TRACK_MODIFICATIONS', 'False').lower() in ['true', '1', 't']
    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
    # For generating secure tokens later
    SECURITY_PASSWORD_SALT = os.getenv('SECURITY_PASSWORD_SALT', 'a_default_salt_for_development')
    
    # Email server configuration for Gmail
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    # This securely reads the credentials from your .env file
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = ('Bookmark API', os.getenv('MAIL_USERNAME'))

class DevConfig(Config):
    """Development configuration."""
    DEBUG = True

class ProdConfig(Config):
    """Production configuration."""
    DEBUG = False

# Dictionary to access configs by name
config_by_name = {
    'development': DevConfig,
    'production': ProdConfig,
}