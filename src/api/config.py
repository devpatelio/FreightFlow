import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY')
    SUPABASE_JWT_SECRET = os.getenv('SUPABASE_JWT_SECRET', '')

    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')

    if os.getenv('VERCEL'):
        UPLOAD_FOLDER = Path('/tmp/uploads')
        EXPORT_FOLDER = Path('/tmp/export')
    else:
        UPLOAD_FOLDER = Path(__file__).parent.parent.parent / 'uploads'
        EXPORT_FOLDER = Path(__file__).parent.parent.parent / 'export'


def ensure_dirs():
    """Create upload/export directories if they don't exist."""
    try:
        Config.UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
        Config.EXPORT_FOLDER.mkdir(parents=True, exist_ok=True)
    except (OSError, PermissionError):
        pass
