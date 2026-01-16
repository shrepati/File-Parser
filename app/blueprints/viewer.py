"""
Viewer Blueprint
Handles file reading and downloading
"""

import os
from flask import Blueprint, jsonify, send_from_directory

from app.database import db_session
from app.models import Job
from app.utils.security import check_file_access, check_file_size, is_binary_file, get_file_size_human
from config import settings

viewer_bp = Blueprint('viewer', __name__)


@viewer_bp.route('/read/<job_id>/<path:file_path>', methods=['GET'])
def read_file(job_id, file_path):
    """
    Read file content (text files only, max 5MB)

    Args:
        job_id: UUID of the job
        file_path: Relative path to file
    """
    # Validate job exists
    job = db_session.query(Job).filter_by(id=job_id).first()
    if not job:
        return jsonify({'error': 'Job not found'}), 404

    # Security check
    is_safe, full_path, error = check_file_access(job_id, file_path)
    if not is_safe:
        return jsonify({'error': error}), 403 if 'denied' in error.lower() else 404

    # Check if it's a directory
    if os.path.isdir(full_path):
        return jsonify({'error': 'Cannot read directory'}), 400

    # Check file size
    is_valid_size, size, size_error = check_file_size(full_path)
    if not is_valid_size:
        return jsonify({
            'error': 'File too large for preview',
            'size': get_file_size_human(size),
            'message': size_error
        }), 413

    # Check if binary
    if is_binary_file(full_path):
        return jsonify({
            'error': 'Binary file',
            'message': 'This file appears to be binary and cannot be displayed as text',
            'size': get_file_size_human(size)
        }), 415

    # Read file content
    try:
        with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()

        return jsonify({
            'success': True,
            'content': content,
            'size': size,
            'size_human': get_file_size_human(size)
        })

    except Exception as e:
        return jsonify({
            'error': 'Error reading file',
            'message': str(e)
        }), 500


@viewer_bp.route('/download/<job_id>/<path:file_path>', methods=['GET'])
def download_file(job_id, file_path):
    """
    Download a file

    Args:
        job_id: UUID of the job
        file_path: Relative path to file
    """
    # Validate job exists
    job = db_session.query(Job).filter_by(id=job_id).first()
    if not job:
        return jsonify({'error': 'Job not found'}), 404

    # Security check
    is_safe, full_path, error = check_file_access(job_id, file_path)
    if not is_safe:
        return jsonify({'error': error}), 403 if 'denied' in error.lower() else 404

    # Check if it's a directory
    if os.path.isdir(full_path):
        return jsonify({'error': 'Cannot download directory'}), 400

    # Send file
    directory = os.path.dirname(full_path)
    filename = os.path.basename(full_path)

    return send_from_directory(directory, filename, as_attachment=True)
