import os
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()

class Config:
    # Use a persistent secret key if env var not set to avoid session invalidation on restart
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'persistent-secret-key-777-dargon'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///site.db'
    if SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session Security
    REMEMBER_COOKIE_DURATION = timedelta(days=30)
    SESSION_PROTECTION = "basic" # Less aggressive than 'strong' to prevent logout on minor IP changes
