"""
Indexing Service
Indexes extracted files for search and browsing
"""

import os
from datetime import datetime

from app.database import db_session
from app.models import Job, FileMetadata
from app.utils.file_utils import get_file_extension, format_file_info
from config import settings
import logging

logger = logging.getLogger(__name__)


class IndexingService:
    """Handles file indexing for search and browsing"""

    def index_extraction(self, job_id):
        """
        Index all files from an extraction (OPTIMIZED for speed)

        Args:
            job_id: UUID of the job to index

        Returns:
            dict: Indexing statistics
        """
        extract_path = os.path.join(settings.EXTRACT_FOLDER, job_id)

        if not os.path.exists(extract_path):
            logger.error(f"Extraction path not found for job {job_id}")
            return {'error': 'Extraction path not found'}

        stats = {
            'files_indexed': 0,
            'directories_indexed': 0,
            'total_size': 0,
            'rhoso_folders': []
        }

        try:
            batch_items = []
            batch_size = 500  # Commit every 500 items for better performance

            # Walk through all files and directories
            for root, dirs, files in os.walk(extract_path):
                # Index directories
                for dir_name in dirs:
                    dir_path = os.path.join(root, dir_name)
                    rel_path = os.path.relpath(dir_path, extract_path)
                    parent_path = os.path.dirname(rel_path) if rel_path != '.' else None

                    # Check if this is a RHOSO test folder
                    if dir_name.startswith('rhoso'):
                        stats['rhoso_folders'].append(rel_path)

                    # Create metadata entry (batched)
                    metadata = FileMetadata(
                        job_id=job_id,
                        name=dir_name,
                        path=dir_path,
                        relative_path=rel_path,
                        size=None,
                        extension=None,
                        is_directory=True,
                        parent_path=parent_path,
                        content_preview=None
                    )
                    batch_items.append(metadata)
                    stats['directories_indexed'] += 1

                    # Batch commit for performance
                    if len(batch_items) >= batch_size:
                        db_session.bulk_save_objects(batch_items)
                        db_session.commit()
                        batch_items = []

                # Index files
                for filename in files:
                    file_path = os.path.join(root, filename)
                    rel_path = os.path.relpath(file_path, extract_path)
                    parent_path = os.path.dirname(rel_path) if rel_path != '.' else None

                    try:
                        file_size = os.path.getsize(file_path)
                        stats['total_size'] += file_size

                        # OPTIMIZATION: Skip content preview - not needed for browsing
                        # This saves thousands of file reads

                        # Create metadata entry (batched)
                        metadata = FileMetadata(
                            job_id=job_id,
                            name=filename,
                            path=file_path,
                            relative_path=rel_path,
                            size=file_size,
                            extension=get_file_extension(filename),
                            is_directory=False,
                            parent_path=parent_path,
                            content_preview=None  # Skip for speed
                        )
                        batch_items.append(metadata)
                        stats['files_indexed'] += 1

                        # Batch commit for performance
                        if len(batch_items) >= batch_size:
                            db_session.bulk_save_objects(batch_items)
                            db_session.commit()
                            batch_items = []

                    except (PermissionError, OSError) as e:
                        logger.warning(f"Skipped indexing {file_path}: {e}")

            # Commit remaining items
            if batch_items:
                db_session.bulk_save_objects(batch_items)
                db_session.commit()

            # Update job with statistics
            job = db_session.query(Job).filter_by(id=job_id).first()
            if job:
                job.total_files = stats['files_indexed']
                job.total_directories = stats['directories_indexed']
                job.total_size = stats['total_size']
                job.has_rhoso_tests = len(stats['rhoso_folders']) > 0
                job.status = 'completed'
                job.progress = 100
                job.message = 'Extraction completed'
                job.updated_at = datetime.utcnow()

            db_session.commit()
            logger.info(f"FAST INDEXED {stats['files_indexed']} files and {stats['directories_indexed']} directories for job {job_id}")

        except Exception as e:
            logger.error(f"Error indexing job {job_id}: {e}", exc_info=True)
            db_session.rollback()
            stats['error'] = str(e)

        return stats

    def _get_content_preview(self, file_path, max_chars=500):
        """
        Get content preview for text files

        Args:
            file_path: Path to file
            max_chars: Maximum characters to read

        Returns:
            str: Content preview or None if binary/error
        """
        try:
            # Only preview small text files
            if os.path.getsize(file_path) > 1024 * 1024:  # 1MB limit
                return None

            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(max_chars)
                return content
        except Exception:
            return None

    def search_files(self, job_id, query, file_type=None):
        """
        Search indexed files

        Args:
            job_id: UUID of the job
            query: Search query string
            file_type: Optional filter ('file' or 'directory')

        Returns:
            list: Matching file metadata
        """
        query_lower = query.lower()

        # Build base query
        results = db_session.query(FileMetadata).filter_by(job_id=job_id)

        # Filter by type
        if file_type == 'file':
            results = results.filter_by(is_directory=False)
        elif file_type == 'directory':
            results = results.filter_by(is_directory=True)

        # Search in name, path, and content preview
        results = results.filter(
            (FileMetadata.name.ilike(f'%{query_lower}%')) |
            (FileMetadata.relative_path.ilike(f'%{query_lower}%')) |
            (FileMetadata.content_preview.ilike(f'%{query_lower}%'))
        ).all()

        return [r.to_dict() for r in results]


# Global indexing service instance
indexing_service = IndexingService()
