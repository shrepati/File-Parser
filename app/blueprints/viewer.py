"""
Viewer Blueprint
Handles file reading and downloading
"""

import os
import logging
from flask import Blueprint, jsonify, send_from_directory

from app.database import db_session
from app.models import Job, FileMetadata
from app.utils.security import check_file_access, check_file_size, is_binary_file, get_file_size_human
from app.services.rhcert_extractor import RHCertAttachmentExtractor
from config import settings

logger = logging.getLogger(__name__)

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


@viewer_bp.route('/extract-rhcert/<job_id>/<path:file_path>', methods=['POST'])
def extract_rhcert_attachments(job_id, file_path):
    """
    Extract embedded attachments from rhcert XML file

    Args:
        job_id: UUID of the job
        file_path: Relative path to rhcert XML file
    """
    # Validate job exists
    job = db_session.query(Job).filter_by(id=job_id).first()
    if not job:
        return jsonify({'error': 'Job not found'}), 404

    # Security check
    is_safe, full_path, error = check_file_access(job_id, file_path)
    if not is_safe:
        return jsonify({'error': error}), 403 if 'denied' in error.lower() else 404

    # Check if it's an XML file
    if not file_path.lower().endswith('.xml'):
        return jsonify({'error': 'Not an XML file'}), 400

    # Check if it's a rhcert file
    if 'rhcert-results' not in os.path.basename(file_path).lower():
        return jsonify({'error': 'Not a rhcert results file'}), 400

    try:
        # Get extraction base directory (same as job extraction directory)
        extraction_dir = os.path.join(settings.EXTRACT_FOLDER, job_id)

        # Initialize extractor
        extractor = RHCertAttachmentExtractor(full_path, extraction_dir)

        # Extract all attachments
        logger.info(f"Extracting attachments from rhcert XML: {file_path}")
        results = extractor.extract_all_attachments()

        # Index extracted files in database
        indexed_count = _index_extracted_files(job_id, results, extraction_dir)

        return jsonify({
            'success': True,
            'message': 'Attachments extracted successfully',
            'total_attachments': results['total_attachments'],
            'extracted_files': len(results['extracted_files']),
            'extracted_archives': len(results['extracted_archives']),
            'indexed_files': indexed_count,
            'errors': results['errors']
        })

    except Exception as e:
        logger.error(f"Error extracting rhcert attachments: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': 'Extraction failed',
            'message': str(e)
        }), 500


def _index_extracted_files(job_id: str, extraction_results: dict, extraction_dir: str) -> int:
    """
    Index extracted files in database so they appear in file browser

    Args:
        job_id: Job UUID
        extraction_results: Results from extraction
        extraction_dir: Base extraction directory

    Returns:
        int: Number of files indexed
    """
    indexed_count = 0

    try:
        # Index direct attachments
        for file_info in extraction_results['extracted_files']:
            # Check if already indexed
            existing = db_session.query(FileMetadata).filter_by(
                job_id=job_id,
                relative_path=file_info['relative_path']
            ).first()

            if not existing:
                # Get file details
                file_path = file_info['path']
                file_name = os.path.basename(file_path)
                file_size = file_info['size']
                file_ext = os.path.splitext(file_name)[1]

                # Create metadata entry
                metadata = FileMetadata(
                    job_id=job_id,
                    name=file_name,
                    path=file_path,
                    relative_path=file_info['relative_path'],
                    size=file_size,
                    extension=file_ext,
                    is_directory=False,
                    parent_path='rhcert_attachments'
                )

                db_session.add(metadata)
                indexed_count += 1

        # Index files extracted from archives
        for archive_result in extraction_results['extracted_archives']:
            for file_info in archive_result['extracted_files']:
                # Check if already indexed
                existing = db_session.query(FileMetadata).filter_by(
                    job_id=job_id,
                    relative_path=file_info['relative_path']
                ).first()

                if not existing:
                    file_path = file_info['path']
                    file_name = os.path.basename(file_path)
                    file_size = file_info['size']
                    file_ext = os.path.splitext(file_name)[1]

                    # Determine parent path
                    rel_path_parts = file_info['relative_path'].split('/')
                    parent_path = '/'.join(rel_path_parts[:-1]) if len(rel_path_parts) > 1 else ''

                    metadata = FileMetadata(
                        job_id=job_id,
                        name=file_name,
                        path=file_path,
                        relative_path=file_info['relative_path'],
                        size=file_size,
                        extension=file_ext,
                        is_directory=False,
                        parent_path=parent_path
                    )

                    db_session.add(metadata)
                    indexed_count += 1

        db_session.commit()
        logger.info(f"Indexed {indexed_count} extracted files in database")

    except Exception as e:
        logger.error(f"Error indexing extracted files: {e}")
        db_session.rollback()

    return indexed_count
