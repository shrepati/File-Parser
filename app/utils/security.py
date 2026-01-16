"""
Security Utilities
All path validation, filename sanitization, and security checks
"""

import os
from werkzeug.utils import secure_filename as werkzeug_secure_filename
from config import settings


def secure_filename(filename):
    """
    Sanitize uploaded filenames to prevent directory traversal
    Uses Werkzeug's secure_filename function
    """
    return werkzeug_secure_filename(filename)


def validate_path_traversal(full_path, base_path):
    """
    Prevent path traversal attacks

    Args:
        full_path: The constructed path to validate
        base_path: The allowed base directory

    Returns:
        bool: True if path is safe, False otherwise

    Example:
        >>> validate_path_traversal('/app/extracted/job123/file.txt', '/app/extracted/job123')
        True
        >>> validate_path_traversal('/app/extracted/job123/../../../etc/passwd', '/app/extracted/job123')
        False
    """
    abs_full_path = os.path.abspath(full_path)
    abs_base_path = os.path.abspath(base_path)

    return abs_full_path.startswith(abs_base_path)


def allowed_file(filename):
    """
    Check if file extension is in the allowed list

    Args:
        filename: The filename to check

    Returns:
        bool: True if extension is allowed, False otherwise
    """
    if '.' not in filename:
        return False

    extension = filename.rsplit('.', 1)[1].lower()
    return extension in settings.ALLOWED_EXTENSIONS


def check_file_access(job_id, file_path, extract_folder=None):
    """
    Comprehensive security check for file access

    Args:
        job_id: The job ID
        file_path: Relative path within the extraction
        extract_folder: Base extraction folder (defaults to settings.EXTRACT_FOLDER)

    Returns:
        tuple: (is_safe: bool, full_path: str, error_message: str|None)

    Example:
        >>> is_safe, full_path, error = check_file_access('job123', 'file.txt')
        >>> if not is_safe:
        ...     return error_message
    """
    if extract_folder is None:
        extract_folder = settings.EXTRACT_FOLDER

    # Build paths
    job_extract_path = os.path.join(extract_folder, job_id)
    full_path = os.path.join(job_extract_path, file_path) if file_path else job_extract_path

    # Check if extraction folder exists
    if not os.path.exists(job_extract_path):
        return False, None, 'Extraction folder not found'

    # Path traversal check
    if not validate_path_traversal(full_path, job_extract_path):
        return False, None, 'Access denied - path traversal attempt detected'

    # Check if path exists
    if not os.path.exists(full_path):
        return False, None, 'File or directory not found'

    return True, full_path, None


def check_file_size(file_path, max_size=None):
    """
    Check if file size is within limits

    Args:
        file_path: Path to the file
        max_size: Maximum allowed size in bytes (defaults to settings.MAX_PREVIEW_SIZE)

    Returns:
        tuple: (is_valid: bool, size: int, error_message: str|None)
    """
    if max_size is None:
        max_size = settings.MAX_PREVIEW_SIZE

    try:
        size = os.path.getsize(file_path)
        if size > max_size:
            return False, size, f'File size ({get_file_size_human(size)}) exceeds maximum allowed ({get_file_size_human(max_size)})'
        return True, size, None
    except OSError as e:
        return False, 0, f'Error reading file size: {str(e)}'


def is_binary_file(file_path):
    """
    Detect if a file is binary

    Args:
        file_path: Path to the file

    Returns:
        bool: True if file appears to be binary, False if text
    """
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(1024)
            # Check for null bytes (common in binary files)
            if b'\0' in chunk:
                return True
            # Try to decode as UTF-8
            try:
                chunk.decode('utf-8')
                return False
            except UnicodeDecodeError:
                return True
    except Exception:
        return True


def get_file_size_human(size):
    """
    Convert bytes to human readable format

    Args:
        size: Size in bytes

    Returns:
        str: Human-readable size string

    Example:
        >>> get_file_size_human(1536)
        '1.50 KB'
        >>> get_file_size_human(2097152)
        '2.00 MB'
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"
