import os

class Config:
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///hospital_management.db")
    SECRET_KEY = os.getenv("SECRET_KEY", "your_secret_key")
    DEBUG = os.getenv("DEBUG", "False") == "True"
    ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "").split(",") if os.getenv("ALLOWED_HOSTS") else []
    GDPR_COMPLIANCE = True  # Ensure GDPR compliance is enabled

    @staticmethod
    def init_app(app):
        pass 