import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_TRACK_MODIFICATIONS = os.environ.get('SQLALCHEMY_TRACK_MODIFICATIONS', 'False').lower() in ['true', '1', 't']
    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')

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