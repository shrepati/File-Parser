"""
Tree Builder Service
Builds hierarchical directory tree structures
"""

import os
from collections import defaultdict

from app.database import db_session
from app.models import FileMetadata
from config import settings
import logging

logger = logging.getLogger(__name__)


class TreeBuilderService:
    """Builds directory tree structures for visualization"""

    def build_tree(self, job_id, start_path=''):
        """
        Build tree structure from indexed files

        Args:
            job_id: UUID of the job
            start_path: Starting path (empty for root)

        Returns:
            dict: Tree structure
        """
        # Query all files and directories
        all_items = db_session.query(FileMetadata).filter_by(job_id=job_id).all()

        if not all_items:
            return {
                'name': 'root',
                'path': '',
                'type': 'directory',
                'children': []
            }

        # Build tree structure
        tree = self._build_tree_recursive(all_items, start_path)
        return tree

    def _build_tree_recursive(self, items, start_path):
        """
        Recursively build tree structure

        Args:
            items: List of FileMetadata objects
            start_path: Current path prefix

        Returns:
            dict: Tree node
        """
        # Group items by their immediate parent
        children_by_parent = defaultdict(list)

        for item in items:
            rel_path = item.relative_path

            # Skip if not in current path
            if start_path and not rel_path.startswith(start_path):
                continue

            # Get relative path from start_path
            if start_path:
                path_from_start = rel_path[len(start_path):].lstrip('/')
            else:
                path_from_start = rel_path

            # Get immediate parent
            if '/' in path_from_start:
                parent = path_from_start.split('/')[0]
            else:
                parent = ''

            children_by_parent[parent].append(item)

        # Build root node
        root = {
            'name': os.path.basename(start_path) if start_path else 'root',
            'path': start_path,
            'type': 'directory',
            'children': []
        }

        # Add immediate children
        for item in children_by_parent.get('', []):
            if item.is_directory:
                # Add directory node
                dir_node = {
                    'name': item.name,
                    'path': item.relative_path,
                    'type': 'directory',
                    'file_count': self._count_files(items, item.relative_path),
                    'children': []  # Children loaded lazily
                }
                root['children'].append(dir_node)
            else:
                # Add file node
                file_node = {
                    'name': item.name,
                    'path': item.relative_path,
                    'type': 'file',
                    'size': item.size,
                    'extension': item.extension
                }
                root['children'].append(file_node)

        # Sort children: directories first, then files, alphabetically
        root['children'].sort(key=lambda x: (x['type'] == 'file', x['name'].lower()))

        return root

    def _count_files(self, items, dir_path):
        """Count files in a directory"""
        count = 0
        for item in items:
            if not item.is_directory and item.relative_path.startswith(dir_path + '/'):
                count += 1
        return count

    def get_directory_contents(self, job_id, dir_path=''):
        """
        Get immediate contents of a directory

        Args:
            job_id: UUID of the job
            dir_path: Directory path (empty for root)

        Returns:
            dict: Directory contents with files and subdirectories
        """
        # Query items in this directory
        if dir_path:
            items = db_session.query(FileMetadata).filter(
                FileMetadata.job_id == job_id,
                FileMetadata.parent_path == dir_path
            ).all()
        else:
            # Root level: find the root directory first, then get its children
            root_dir = db_session.query(FileMetadata).filter(
                FileMetadata.job_id == job_id,
                FileMetadata.is_directory == True,
                (FileMetadata.parent_path == None) | (FileMetadata.parent_path == '') | (FileMetadata.parent_path == '.')
            ).first()

            if root_dir:
                # Get children of the root directory
                items = db_session.query(FileMetadata).filter(
                    FileMetadata.job_id == job_id,
                    FileMetadata.parent_path == root_dir.relative_path
                ).all()
            else:
                # Fallback: get items with no parent
                items = db_session.query(FileMetadata).filter(
                    FileMetadata.job_id == job_id,
                    (FileMetadata.parent_path == None) | (FileMetadata.parent_path == '') | (FileMetadata.parent_path == '.')
                ).all()

        files = []
        directories = []

        for item in items:
            if item.is_directory:
                directories.append({
                    'name': item.name,
                    'path': item.relative_path,
                    'relative_path': item.relative_path,
                    'type': 'directory',
                    'size': item.size,
                    'size_human': 'Directory'
                })
            else:
                from app.utils.security import get_file_size_human
                files.append({
                    'name': item.name,
                    'path': item.relative_path,
                    'relative_path': item.relative_path,
                    'type': 'file',
                    'size': item.size,
                    'size_human': get_file_size_human(item.size) if item.size else 'Unknown',
                    'extension': item.extension
                })

        # Sort alphabetically
        files.sort(key=lambda x: x['name'].lower())
        directories.sort(key=lambda x: x['name'].lower())

        return {
            'files': files,
            'directories': directories,
            'current_path': dir_path
        }


# Global tree builder service instance
tree_builder_service = TreeBuilderService()
