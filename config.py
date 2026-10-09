import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
DATABASE = os.environ.get("DATABASE", os.path.join(BASE_DIR, "placement.db"))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
ALLOWED_RESUME_EXTS = {".pdf", ".doc", ".docx", ".txt"}
MAX_UPLOAD_MB = 2
