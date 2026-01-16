"""
Browse Blueprint
Handles file browsing, search, pagination, and tree view
"""

from flask import Blueprint, request, jsonify

from app.database import db_session
from app.models import Job
from app.services.indexing import indexing_service
from app.services.tree_builder import tree_builder_service
from app.utils.pagination import paginate, get_pagination_params, sort_items
from config import settings

browse_bp = Blueprint('browse', __name__)


@browse_bp.route('/browse/<job_id>', methods=['GET'])
@browse_bp.route('/browse/<job_id>/<path:dir_path>', methods=['GET'])
def browse_files(job_id, dir_path=''):
    """
    Browse files and directories

    Args:
        job_id: UUID of the job
        dir_path: Optional subdirectory path

    Query params:
        page: Page number (default 1)
        per_page: Items per page (default 50)
        sort: Sort field (default 'name')
        dir: Sort direction 'asc' or 'desc' (default 'asc')
    """
    # Validate job exists
    job = db_session.query(Job).filter_by(id=job_id).first()
    if not job:
        return jsonify({'error': 'Job not found'}), 404

    # Get pagination parameters
    page, per_page, sort_by, sort_order = get_pagination_params(request)

    # Get directory contents
    contents = tree_builder_service.get_directory_contents(job_id, dir_path)

    # Combine files and directories
    all_items = contents['directories'] + contents['files']

    # Sort items
    sorted_items = sort_items(all_items, sort_by, sort_order)

    # Paginate
    result = paginate(sorted_items, page, per_page)

    # Add job and path info
    result['job_id'] = job_id
    result['current_path'] = dir_path

    return jsonify(result)


@browse_bp.route('/search/<job_id>', methods=['GET'])
def search_files(job_id):
    """
    Search files by name or content

    Args:
        job_id: UUID of the job

    Query params:
        q: Search query
        type: Filter by 'file' or 'directory' (optional)
        page: Page number (default 1)
        per_page: Items per page (default 50)
    """
    # Validate job exists
    job = db_session.query(Job).filter_by(id=job_id).first()
    if not job:
        return jsonify({'error': 'Job not found'}), 404

    # Get search parameters
    query = request.args.get('q', '')
    file_type = request.args.get('type', None)

    if not query:
        return jsonify({'error': 'Search query required'}), 400

    # Get pagination parameters
    page, per_page, sort_by, sort_order = get_pagination_params(request)

    # Perform search
    results = indexing_service.search_files(job_id, query, file_type)

    # Sort results
    sorted_results = sort_items(results, sort_by, sort_order)

    # Paginate
    paginated_result = paginate(sorted_results, page, per_page)

    # Add search info
    paginated_result['query'] = query
    paginated_result['job_id'] = job_id

    return jsonify(paginated_result)


@browse_bp.route('/tree/<job_id>', methods=['GET'])
@browse_bp.route('/tree/<job_id>/<path:start_path>', methods=['GET'])
def get_tree(job_id, start_path=''):
    """
    Get directory tree structure

    Args:
        job_id: UUID of the job
        start_path: Optional starting path

    Query params:
        expand: Whether to expand all nodes (default false)
    """
    # Validate job exists
    job = db_session.query(Job).filter_by(id=job_id).first()
    if not job:
        return jsonify({'error': 'Job not found'}), 404

    # Build tree
    tree = tree_builder_service.build_tree(job_id, start_path)

    return jsonify({
        'tree': tree,
        'job_id': job_id
    })


@browse_bp.route('/all-files/<job_id>', methods=['GET'])
def get_all_files(job_id):
    """
    Get all files and directories for tree building

    Args:
        job_id: UUID of the job
    """
    # Validate job exists
    job = db_session.query(Job).filter_by(id=job_id).first()
    if not job:
        return jsonify({'error': 'Job not found'}), 404

    from app.models import FileMetadata
    from app.utils.security import get_file_size_human

    # Get all files and directories
    all_items = db_session.query(FileMetadata).filter_by(job_id=job_id).all()

    items = []
    for item in all_items:
        items.append({
            'name': item.name,
            'relative_path': item.relative_path,
            'type': 'directory' if item.is_directory else 'file',
            'size': item.size,
            'size_human': get_file_size_human(item.size) if item.size and not item.is_directory else 'Directory' if item.is_directory else 'Unknown',
            'extension': item.extension if not item.is_directory else None
        })

    return jsonify({
        'job_id': job_id,
        'items': items,
        'total': len(items)
    })


@browse_bp.route('/summary/<job_id>', methods=['GET'])
def get_summary(job_id):
    """
    Get summary report for an extraction

    Args:
        job_id: UUID of the job
    """
    # Validate job exists
    job = db_session.query(Job).filter_by(id=job_id).first()
    if not job:
        return jsonify({'error': 'Job not found'}), 404

    # Get file type breakdown
    from app.models import FileMetadata
    from collections import Counter

    all_files = db_session.query(FileMetadata).filter_by(
        job_id=job_id,
        is_directory=False
    ).all()

    # Count by extension
    extensions = Counter(f.extension or 'no extension' for f in all_files)

    # Get largest files
    largest_files = sorted(all_files, key=lambda f: f.size or 0, reverse=True)[:10]

    # Get rhoso folders
    rhoso_folders = db_session.query(FileMetadata).filter(
        FileMetadata.job_id == job_id,
        FileMetadata.is_directory == True,
        FileMetadata.name.like('rhoso%')
    ).all()

    from app.utils.security import get_file_size_human

    return jsonify({
        'job_id': job_id,
        'filename': job.filename,
        'total_files': job.total_files,
        'total_directories': job.total_directories,
        'total_size': job.total_size,
        'total_size_human': get_file_size_human(job.total_size) if job.total_size else '0 B',
        'file_types': dict(extensions.most_common(10)),
        'largest_files': [
            {
                'name': f.name,
                'path': f.relative_path,
                'size': f.size,
                'size_human': get_file_size_human(f.size) if f.size else 'Unknown'
            }
            for f in largest_files
        ],
        'has_rhoso_tests': job.has_rhoso_tests,
        'rhoso_folders': [f.relative_path for f in rhoso_folders]
    })
