#!/usr/bin/env python3
"""
Main Application Entry Point
Runs the Flask application
"""

from app import create_app
from config import settings

app = create_app()

if __name__ == '__main__':
    print("=" * 70)
    print("File Extractor - AI-Powered Test Analysis Platform")
    print("=" * 70)
    print(f"Environment: {settings.FLASK_ENV}")
    print(f"Upload folder: {settings.UPLOAD_FOLDER}")
    print(f"Extract folder: {settings.EXTRACT_FOLDER}")
    print(f"Database: {settings.DATABASE_URL}")
    print(f"Starting server on http://localhost:5000")
    print("=" * 70)
    print()

    app.run(
        debug=settings.DEBUG,
        host='0.0.0.0',
        port=5000
    )
