"""
Pagination Utilities
Helper functions for paginating large result sets
"""

import math
from config import settings


def paginate(items, page=1, per_page=None):
    """
    Paginate a list of items

    Args:
        items: List of items to paginate
        page: Page number (1-indexed)
        per_page: Items per page (defaults to settings.DEFAULT_PAGE_SIZE)

    Returns:
        dict: Paginated result with metadata
    """
    if per_page is None:
        per_page = settings.DEFAULT_PAGE_SIZE

    # Enforce maximum page size
    per_page = min(per_page, settings.MAX_PAGE_SIZE)

    total_items = len(items)
    total_pages = math.ceil(total_items / per_page) if per_page > 0 else 0

    # Validate page number
    page = max(1, min(page, total_pages if total_pages > 0 else 1))

    # Calculate slice indices
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page

    # Slice items
    page_items = items[start_idx:end_idx]

    return {
        'items': page_items,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total_items': total_items,
            'total_pages': total_pages,
            'has_next': page < total_pages,
            'has_prev': page > 1,
            'start_index': start_idx + 1 if page_items else 0,
            'end_index': start_idx + len(page_items),
        }
    }


def get_pagination_params(request):
    """
    Extract pagination parameters from Flask request

    Args:
        request: Flask request object

    Returns:
        tuple: (page, per_page, sort_by, sort_order)
    """
    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        page = 1

    try:
        per_page = int(request.args.get('per_page', settings.DEFAULT_PAGE_SIZE))
    except ValueError:
        per_page = settings.DEFAULT_PAGE_SIZE

    sort_by = request.args.get('sort', 'name')
    sort_order = request.args.get('dir', 'asc')

    return page, per_page, sort_by, sort_order


def sort_items(items, sort_by='name', sort_order='asc'):
    """
    Sort items by specified field

    Args:
        items: List of dictionaries to sort
        sort_by: Field name to sort by
        sort_order: 'asc' or 'desc'

    Returns:
        list: Sorted items
    """
    reverse = sort_order.lower() == 'desc'

    try:
        return sorted(items, key=lambda x: x.get(sort_by, ''), reverse=reverse)
    except (TypeError, KeyError):
        # Fallback to name sorting if specified field doesn't exist
        return sorted(items, key=lambda x: x.get('name', ''), reverse=reverse)
