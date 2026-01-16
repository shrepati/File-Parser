"""
Application Configuration
Centralized settings management with environment variable support
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Flask Configuration
SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
FLASK_ENV = os.getenv('FLASK_ENV', 'development')
DEBUG = FLASK_ENV == 'development'

# Database Configuration
DATABASE_URL = os.getenv('DATABASE_URL', f'sqlite:///{BASE_DIR}/data/app.db')

# File Upload Configuration
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', str(BASE_DIR / 'uploads'))
EXTRACT_FOLDER = os.getenv('EXTRACT_FOLDER', str(BASE_DIR / 'extracted'))
MAX_UPLOAD_SIZE = int(os.getenv('MAX_UPLOAD_SIZE', 2 * 1024 * 1024 * 1024))  # 2GB
ALLOWED_EXTENSIONS = {'zip', 'tar', 'gz', 'bz2', 'xz', 'tgz', 'rar', '7z'}

# File Preview Configuration
MAX_PREVIEW_SIZE = 5 * 1024 * 1024  # 5MB

# Pagination Configuration
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 100

# Analysis Service Configuration
ANALYSIS_SERVICE_URL = os.getenv('ANALYSIS_SERVICE_URL', 'http://localhost:8001')
ENABLE_AI_ANALYSIS = os.getenv('ENABLE_AI_ANALYSIS', 'true').lower() == 'true'

# AI Backend Configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY', '')
MCP_SERVER_URL = os.getenv('MCP_SERVER_URL', 'http://localhost:9000')

# CORS Configuration
CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*').split(',')

# Feature Flags
ENABLE_SEARCH = os.getenv('ENABLE_SEARCH', 'true').lower() == 'true'
ENABLE_TREE_VIEW = os.getenv('ENABLE_TREE_VIEW', 'true').lower() == 'true'

# Create required directories
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(EXTRACT_FOLDER, exist_ok=True)
os.makedirs(BASE_DIR / 'data', exist_ok=True)
