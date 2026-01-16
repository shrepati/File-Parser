"""
File Utilities
File type detection, size formatting, and other file operations
"""

import os
from config import settings
from app.utils.security import get_file_size_human


def get_file_extension(filename):
    """
    Extract file extension

    Args:
        filename: The filename

    Returns:
        str: File extension (lowercase, with dot) or empty string
    """
    if '.' not in filename:
        return ''
    return os.path.splitext(filename)[1].lower()


def get_file_type_category(extension):
    """
    Categorize files by extension

    Args:
        extension: File extension (with or without dot)

    Returns:
        str: Category name
    """
    if not extension:
        return 'Other'

    ext = extension.lower().lstrip('.')

    categories = {
        'Code': ['py', 'js', 'java', 'cpp', 'c', 'h', 'cs', 'go', 'rb', 'php', 'sh', 'bash'],
        'Config': ['json', 'yaml', 'yml', 'toml', 'ini', 'conf', 'cfg', 'xml'],
        'Documents': ['txt', 'md', 'pdf', 'doc', 'docx', 'odt', 'rtf'],
        'Logs': ['log', 'out', 'err'],
        'Archives': ['zip', 'tar', 'gz', 'bz2', 'xz', 'tgz', '7z', 'rar'],
        'Images': ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'svg', 'ico'],
        'Data': ['csv', 'tsv', 'sql', 'db', 'sqlite'],
    }

    for category, extensions in categories.items():
        if ext in extensions:
            return category

    return 'Other'


def format_file_info(file_path, relative_path=None):
    """
    Get formatted file information

    Args:
        file_path: Absolute path to file
        relative_path: Relative path for display (optional)

    Returns:
        dict: File information dictionary
    """
    if relative_path is None:
        relative_path = os.path.basename(file_path)

    try:
        stat = os.stat(file_path)
        size = stat.st_size
        is_dir = os.path.isdir(file_path)

        return {
            'name': os.path.basename(file_path),
            'path': relative_path,
            'size': size if not is_dir else None,
            'size_human': get_file_size_human(size) if not is_dir else 'Directory',
            'extension': get_file_extension(file_path) if not is_dir else None,
            'is_directory': is_dir,
            'type_category': get_file_type_category(get_file_extension(file_path)) if not is_dir else 'Directory',
        }
    except OSError:
        return {
            'name': os.path.basename(file_path),
            'path': relative_path,
            'size': None,
            'size_human': 'Unknown',
            'extension': None,
            'is_directory': False,
            'type_category': 'Unknown',
        }
