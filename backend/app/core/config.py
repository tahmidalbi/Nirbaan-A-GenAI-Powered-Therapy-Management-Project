import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # JWT Settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL")

    # CORS
    CORS_ORIGINS: list = ["http://localhost:5173"]

    # Frontend URL (used for building invite links in emails)
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5174")

    # SMTP (optional — leave blank to disable email sending)
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_EMAIL: str = os.getenv("SMTP_EMAIL", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")

settings = Settings()
