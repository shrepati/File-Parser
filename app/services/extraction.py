"""
Archive Extraction Service
Handles ZIP and TAR archive extraction with progress tracking
"""

import os
import zipfile
import tarfile
import threading
from datetime import datetime

from app.database import db_session
from app.models import Job
from config import settings
import logging

logger = logging.getLogger(__name__)


class ExtractionService:
    """Handles archive extraction with progress tracking"""

    def __init__(self):
        self.extraction_progress = {}

    def extract_archive_async(self, job_id, file_path, extract_to):
        """
        Extract archive in background thread

        Args:
            job_id: UUID of the job
            file_path: Path to uploaded archive
            extract_to: Destination directory for extraction
        """
        thread = threading.Thread(
            target=self._extract_archive,
            args=(job_id, file_path, extract_to)
        )
        thread.daemon = True
        thread.start()

    def _extract_archive(self, job_id, file_path, extract_to):
        """
        Extract archive file with progress tracking

        Args:
            job_id: UUID of the job
            file_path: Path to uploaded archive
            extract_to: Destination directory for extraction
        """
        try:
            # Update job status
            self._update_job(job_id, status='extracting', progress=0, message='Initializing extraction...')

            filename = os.path.basename(file_path)
            file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''

            # Handle ZIP archives
            if file_ext == 'zip':
                self._extract_zip(job_id, file_path, extract_to)

            # Handle TAR archives (tar, tar.gz, tar.bz2, tar.xz, tgz)
            elif file_ext in ['tar', 'gz', 'bz2', 'xz', 'tgz'] or 'tar' in filename:
                self._extract_tar(job_id, file_path, extract_to, filename, file_ext)

            else:
                self._update_job(job_id, status='error', progress=0,
                               message=f'Unsupported file format: {file_ext}')
                return

            # Mark extraction as complete and start indexing
            self._update_job(job_id, status='indexing', progress=95,
                           message='Indexing files for search...')

            # Index extracted files
            from app.services.indexing import indexing_service
            indexing_service.index_extraction(job_id)

        except Exception as e:
            logger.error(f"Extraction error for job {job_id}: {str(e)}", exc_info=True)
            self._update_job(job_id, status='error', progress=0, message=f'Error: {str(e)}')

    def _extract_zip(self, job_id, file_path, extract_to):
        """Extract ZIP archive (FAST - bulk extraction)"""
        self._update_job(job_id, status='extracting', progress=10, message='Extracting ZIP archive...')

        try:
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                total_files = len(zip_ref.namelist())

                # Bulk extract - fastest method, no file-by-file iteration
                self._update_job(job_id, progress=50, message=f'Extracting {total_files} files...')
                zip_ref.extractall(extract_to)
                self._update_job(job_id, progress=90, message=f'Extracted {total_files} files')

        except Exception as e:
            logger.error(f"ZIP extraction error: {e}")
            raise

    def _safe_tar_filter(self, member, path):
        """
        Custom TAR filter that safely handles symlinks and absolute paths

        This filter:
        - Strips leading slashes from absolute paths
        - Converts absolute symlinks to relative ones or skips them
        - Skips device files and other dangerous content
        - Allows extraction to continue even with problematic links
        """
        # Skip device files
        if member.isdev():
            return None

        # Handle absolute paths by stripping leading slashes
        if member.name.startswith('/'):
            member.name = member.name.lstrip('/')

        # Handle symlinks
        if member.issym() or member.islnk():
            linkname = member.linkname

            # If symlink points to absolute path, try to make it relative
            if linkname.startswith('/'):
                # Convert absolute symlink to relative by stripping leading slash
                # This makes /path/to/file become path/to/file (relative to extract dir)
                member.linkname = linkname.lstrip('/')
                logger.debug(f"Converted absolute symlink: {member.name} -> {member.linkname}")

        return member

    def _extract_tar(self, job_id, file_path, extract_to, filename, file_ext):
        """Extract TAR archive (FAST - bulk extraction with safe symlink handling)"""
        self._update_job(job_id, status='extracting', progress=10, message='Extracting TAR archive...')

        # Determine compression mode
        mode = 'r'
        if file_ext == 'gz' or filename.endswith('.tar.gz') or file_ext == 'tgz':
            mode = 'r:gz'
        elif file_ext == 'bz2' or filename.endswith('.tar.bz2'):
            mode = 'r:bz2'
        elif file_ext == 'xz' or filename.endswith('.tar.xz'):
            mode = 'r:xz'

        try:
            with tarfile.open(file_path, mode) as tar_ref:
                total_files = len(tar_ref.getmembers())

                # Bulk extract with custom filter for safe symlink handling
                self._update_job(job_id, progress=50, message=f'Extracting {total_files} files...')
                tar_ref.extractall(extract_to, filter=self._safe_tar_filter)
                self._update_job(job_id, progress=90, message=f'Extracted {total_files} files')

        except Exception as e:
            logger.error(f"TAR extraction error: {e}")
            raise

    def _update_job(self, job_id, **kwargs):
        """
        Update job in database

        Args:
            job_id: UUID of the job
            **kwargs: Fields to update (status, progress, message)
        """
        try:
            job = db_session.query(Job).filter_by(id=job_id).first()
            if job:
                for key, value in kwargs.items():
                    setattr(job, key, value)
                job.updated_at = datetime.utcnow()
                db_session.commit()
        except Exception as e:
            logger.error(f"Error updating job {job_id}: {e}")
            db_session.rollback()

    def get_progress(self, job_id):
        """
        Get extraction progress for a job

        Args:
            job_id: UUID of the job

        Returns:
            dict: Progress information or None if not found
        """
        job = db_session.query(Job).filter_by(id=job_id).first()
        if not job:
            return None

        return {
            'status': job.status,
            'progress': job.progress,
            'message': job.message,
        }


# Global extraction service instance
extraction_service = ExtractionService()
