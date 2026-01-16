#!/usr/bin/env python3
"""
File Extractor Web Application
A Flask-based web app for uploading, extracting, and browsing archive files
"""

from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import zipfile
import tarfile
import shutil
import time
import threading
import uuid
from pathlib import Path

app = Flask(__name__)
CORS(app)

# Configuration
UPLOAD_FOLDER = 'uploads'
EXTRACT_FOLDER = 'extracted'
ALLOWED_EXTENSIONS = {'zip', 'tar', 'gz', 'bz2', 'xz', 'tgz', 'rar', '7z'}
MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2GB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['EXTRACT_FOLDER'] = EXTRACT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Store extraction progress
extraction_progress = {}

# Create necessary directories
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(EXTRACT_FOLDER, exist_ok=True)


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_file_size_human(size):
    """Convert bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"


def extract_archive(file_path, extract_to, job_id):
    """Extract archive file with progress tracking"""
    try:
        extraction_progress[job_id] = {
            'status': 'starting',
            'progress': 0,
            'message': 'Initializing extraction...'
        }

        filename = os.path.basename(file_path)
        file_ext = filename.rsplit('.', 1)[1].lower()

        # Handle different archive types
        if file_ext == 'zip':
            extraction_progress[job_id].update({
                'status': 'extracting',
                'progress': 10,
                'message': 'Opening ZIP archive...'
            })

            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                members = zip_ref.namelist()
                total_files = len(members)
                skipped_files = []

                # For small archives (< 1000 files), extract all at once for speed
                if total_files < 1000:
                    try:
                        zip_ref.extractall(extract_to)
                        extraction_progress[job_id].update({
                            'progress': 90,
                            'message': f'Extracted all {total_files} files'
                        })
                    except Exception as e:
                        print(f"Bulk extraction failed, falling back to individual extraction: {e}")
                        # Fall back to individual extraction if bulk fails
                        for member in members:
                            try:
                                zip_ref.extract(member, extract_to)
                            except (PermissionError, OSError) as err:
                                skipped_files.append(member)
                else:
                    # For large archives, extract with progress tracking
                    update_interval = max(1, total_files // 100)  # Update 100 times max

                    for i, member in enumerate(members):
                        try:
                            zip_ref.extract(member, extract_to)
                        except (PermissionError, OSError) as e:
                            # Skip files with permission issues
                            skipped_files.append(member)
                            print(f"Skipped {member}: {e}")

                        # Update progress less frequently for large archives
                        if i % update_interval == 0 or i == total_files - 1:
                            progress = 10 + int((i + 1) / total_files * 80)
                            extraction_progress[job_id].update({
                                'progress': progress,
                                'message': f'Extracting: {i+1}/{total_files} files'
                            })

                if skipped_files:
                    print(f"Skipped {len(skipped_files)} files due to permission errors")

        elif file_ext in ['tar', 'gz', 'bz2', 'xz', 'tgz'] or 'tar' in filename:
            extraction_progress[job_id].update({
                'status': 'extracting',
                'progress': 10,
                'message': 'Opening TAR archive...'
            })

            mode = 'r'
            if file_ext == 'gz' or filename.endswith('.tar.gz') or file_ext == 'tgz':
                mode = 'r:gz'
            elif file_ext == 'bz2' or filename.endswith('.tar.bz2'):
                mode = 'r:bz2'
            elif file_ext == 'xz' or filename.endswith('.tar.xz'):
                mode = 'r:xz'

            with tarfile.open(file_path, mode) as tar_ref:
                members = tar_ref.getmembers()
                total_files = len(members)
                skipped_files = []

                # Update progress every N files for better performance
                update_interval = max(1, total_files // 100)  # Update 100 times max

                for i, member in enumerate(members):
                    try:
                        # Use data_filter to safely handle absolute paths and symlinks
                        # This filter:
                        # - Strips leading slashes from absolute paths
                        # - Makes symlinks relative and safe
                        # - Skips device files
                        tar_ref.extract(member, extract_to, filter='data')
                    except (PermissionError, OSError, tarfile.ExtractError, tarfile.AbsoluteLinkError) as e:
                        # Skip files with permission issues or unsafe links
                        skipped_files.append(member.name)
                        print(f"Skipped {member.name}: {e}")

                    # Update progress less frequently for large archives
                    if i % update_interval == 0 or i == total_files - 1:
                        progress = 10 + int((i + 1) / total_files * 80)
                        extraction_progress[job_id].update({
                            'progress': progress,
                            'message': f'Extracting: {i+1}/{total_files} files'
                        })

                if skipped_files:
                    print(f"Skipped {len(skipped_files)} files due to errors (permissions, unsafe links, etc.)")

        else:
            extraction_progress[job_id].update({
                'status': 'error',
                'progress': 0,
                'message': f'Unsupported file format: {file_ext}'
            })
            return

        extraction_progress[job_id].update({
            'status': 'completed',
            'progress': 100,
            'message': 'Extraction completed successfully!'
        })

    except Exception as e:
        extraction_progress[job_id].update({
            'status': 'error',
            'progress': 0,
            'message': f'Error: {str(e)}'
        })


def scan_directory(path, recursive=True, calculate_dir_sizes=False):
    """Scan directory and return file/folder structure

    Args:
        path: Directory to scan
        recursive: If True, scan all subdirectories
        calculate_dir_sizes: If True, calculate directory sizes (slow for large trees)
    """
    files = []
    directories = []
    total_size = 0

    if recursive:
        # Recursive scan for initial overview
        for root, dirs, filenames in os.walk(path):
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                rel_path = os.path.relpath(dir_path, path)

                # Skip expensive directory size calculation by default
                dir_size = 0
                if calculate_dir_sizes:
                    for r, d, f in os.walk(dir_path):
                        for file in f:
                            fp = os.path.join(r, file)
                            if os.path.exists(fp):
                                try:
                                    dir_size += os.path.getsize(fp)
                                except (PermissionError, OSError):
                                    pass

                directories.append({
                    'name': dir_name,
                    'path': rel_path,
                    'size': dir_size,
                    'size_human': get_file_size_human(dir_size) if dir_size > 0 else 'Unknown'
                })

            for filename in filenames:
                file_path = os.path.join(root, filename)
                rel_path = os.path.relpath(file_path, path)

                if os.path.exists(file_path):
                    try:
                        file_size = os.path.getsize(file_path)
                        total_size += file_size

                        files.append({
                            'name': filename,
                            'path': rel_path,
                            'size': file_size,
                            'size_human': get_file_size_human(file_size),
                            'extension': os.path.splitext(filename)[1].lower()
                        })
                    except (PermissionError, OSError):
                        pass
    else:
        # Non-recursive scan for directory browsing
        try:
            items = os.listdir(path)

            for item in items:
                item_path = os.path.join(path, item)

                if os.path.isdir(item_path):
                    # Skip expensive directory size calculation by default
                    dir_size = 0
                    if calculate_dir_sizes:
                        try:
                            for r, d, f in os.walk(item_path):
                                for file in f:
                                    fp = os.path.join(r, file)
                                    if os.path.exists(fp):
                                        dir_size += os.path.getsize(fp)
                        except (PermissionError, OSError):
                            pass

                    directories.append({
                        'name': item,
                        'path': item,
                        'size': dir_size,
                        'size_human': get_file_size_human(dir_size) if dir_size > 0 else 'Unknown'
                    })
                else:
                    try:
                        file_size = os.path.getsize(item_path)
                        total_size += file_size

                        files.append({
                            'name': item,
                            'path': item,
                            'size': file_size,
                            'size_human': get_file_size_human(file_size),
                            'extension': os.path.splitext(item)[1].lower()
                        })
                    except (PermissionError, OSError):
                        pass
        except (PermissionError, OSError):
            pass

    return {
        'files': sorted(files, key=lambda x: x['name']),
        'directories': sorted(directories, key=lambda x: x['name']),
        'total_size': total_size,
        'total_size_human': get_file_size_human(total_size)
    }


@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle file too large error"""
    return jsonify({
        'error': 'File too large',
        'message': f'File size exceeds the maximum allowed size of {get_file_size_human(MAX_FILE_SIZE)}'
    }), 413


@app.errorhandler(500)
def internal_server_error(error):
    """Handle internal server errors"""
    return jsonify({
        'error': 'Internal server error',
        'message': str(error)
    }), 500


@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400

    # Generate unique job ID
    job_id = str(uuid.uuid4())

    # Save uploaded file
    filename = secure_filename(file.filename)
    upload_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{job_id}_{filename}")
    file.save(upload_path)

    # Create extraction directory
    extract_path = os.path.join(app.config['EXTRACT_FOLDER'], job_id)
    os.makedirs(extract_path, exist_ok=True)

    # Start extraction in background thread
    thread = threading.Thread(target=extract_archive, args=(upload_path, extract_path, job_id))
    thread.start()

    return jsonify({
        'success': True,
        'job_id': job_id,
        'filename': filename
    })


@app.route('/progress/<job_id>')
def get_progress(job_id):
    """Get extraction progress"""
    if job_id not in extraction_progress:
        return jsonify({'error': 'Job not found'}), 404

    return jsonify(extraction_progress[job_id])


@app.route('/browse/<job_id>')
@app.route('/browse/<job_id>/<path:dir_path>')
def browse_files(job_id, dir_path=''):
    """Browse extracted files or directory contents"""
    extract_path = os.path.join(app.config['EXTRACT_FOLDER'], job_id)

    if not os.path.exists(extract_path):
        return jsonify({'error': 'Extraction folder not found'}), 404

    # Build full path
    if dir_path:
        full_path = os.path.join(extract_path, dir_path)
        # Security check
        if not os.path.abspath(full_path).startswith(os.path.abspath(extract_path)):
            return jsonify({'error': 'Access denied'}), 403

        if not os.path.exists(full_path):
            return jsonify({'error': 'Directory not found'}), 404

        if not os.path.isdir(full_path):
            return jsonify({'error': 'Not a directory'}), 400

        browse_path = full_path
    else:
        browse_path = extract_path

    result = scan_directory(browse_path)
    result['job_id'] = job_id
    result['current_path'] = dir_path

    return jsonify(result)


@app.route('/read/<job_id>/<path:file_path>')
def read_file(job_id, file_path):
    """Read file content"""
    extract_path = os.path.join(app.config['EXTRACT_FOLDER'], job_id)
    full_path = os.path.join(extract_path, file_path)

    # Security check: ensure path is within extract folder
    if not os.path.abspath(full_path).startswith(os.path.abspath(extract_path)):
        return jsonify({'error': 'Access denied'}), 403

    if not os.path.exists(full_path):
        return jsonify({'error': 'File not found'}), 404

    if os.path.isdir(full_path):
        return jsonify({'error': 'Cannot read directory'}), 400

    # Check file size
    file_size = os.path.getsize(full_path)
    if file_size > 5 * 1024 * 1024:  # 5MB limit for preview
        return jsonify({
            'error': 'File too large for preview',
            'size': get_file_size_human(file_size),
            'message': 'Files larger than 5MB cannot be previewed in browser'
        }), 413

    try:
        # Try to read as text
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()

        return jsonify({
            'success': True,
            'content': content,
            'size': file_size,
            'size_human': get_file_size_human(file_size)
        })

    except UnicodeDecodeError:
        # Binary file
        return jsonify({
            'error': 'Binary file',
            'message': 'This file appears to be binary and cannot be displayed as text',
            'size': get_file_size_human(file_size)
        }), 415


@app.route('/download/<job_id>/<path:file_path>')
def download_file(job_id, file_path):
    """Download a file"""
    extract_path = os.path.join(app.config['EXTRACT_FOLDER'], job_id)
    full_path = os.path.join(extract_path, file_path)

    # Security check
    if not os.path.abspath(full_path).startswith(os.path.abspath(extract_path)):
        return jsonify({'error': 'Access denied'}), 403

    if not os.path.exists(full_path):
        return jsonify({'error': 'File not found'}), 404

    directory = os.path.dirname(full_path)
    filename = os.path.basename(full_path)

    return send_from_directory(directory, filename, as_attachment=True)


if __name__ == '__main__':
    print("=" * 60)
    print("File Extractor Web Application")
    print("=" * 60)
    print(f"Upload folder: {os.path.abspath(UPLOAD_FOLDER)}")
    print(f"Extract folder: {os.path.abspath(EXTRACT_FOLDER)}")
    print(f"Starting server on http://localhost:5000")
    print("=" * 60)

    app.run(debug=True, host='0.0.0.0', port=5000)
