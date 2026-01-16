"""
Upload Blueprint
Handles file upload and extraction progress tracking
"""

import os
import uuid
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename

from app.database import db_session
from app.models import Job
from app.services.extraction import extraction_service
from app.utils.security import allowed_file
from config import settings

upload_bp = Blueprint('upload', __name__)


@upload_bp.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and start extraction"""

    # Validate request
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400

    # Generate unique job ID
    job_id = str(uuid.uuid4())

    # Secure filename
    filename = secure_filename(file.filename)

    # Save uploaded file
    upload_path = os.path.join(settings.UPLOAD_FOLDER, f"{job_id}_{filename}")
    file.save(upload_path)

    # Create extraction directory
    extract_path = os.path.join(settings.EXTRACT_FOLDER, job_id)
    os.makedirs(extract_path, exist_ok=True)

    # Create job in database
    job = Job(
        id=job_id,
        filename=filename,
        status='uploading',
        progress=0,
        message='File uploaded, preparing extraction...'
    )
    db_session.add(job)
    db_session.commit()

    # Start extraction in background
    extraction_service.extract_archive_async(job_id, upload_path, extract_path)

    return jsonify({
        'success': True,
        'job_id': job_id,
        'filename': filename
    })


@upload_bp.route('/progress/<job_id>', methods=['GET'])
def get_progress(job_id):
    """Get extraction progress for a job"""

    job = db_session.query(Job).filter_by(id=job_id).first()

    if not job:
        return jsonify({'error': 'Job not found'}), 404

    return jsonify({
        'status': job.status,
        'progress': job.progress,
        'message': job.message,
        'has_rhoso_tests': job.has_rhoso_tests
    })
