"""
Job Model - Tracks extraction jobs
"""

from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, Float, DateTime, Text
from app.database import Base


class Job(Base):
    """Represents an archive extraction job"""

    __tablename__ = 'jobs'

    # Primary key
    id = Column(String(36), primary_key=True)  # UUID

    # Job metadata
    filename = Column(String(255), nullable=False)
    status = Column(String(20), nullable=False, default='uploading')
    # Status values: 'uploading', 'extracting', 'indexing', 'completed', 'error'

    progress = Column(Integer, default=0)  # 0-100
    message = Column(Text, nullable=True)

    # Extraction results
    total_files = Column(Integer, default=0)
    total_directories = Column(Integer, default=0)
    total_size = Column(Integer, default=0)  # bytes

    # Test analysis flags
    has_rhoso_tests = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'filename': self.filename,
            'status': self.status,
            'progress': self.progress,
            'message': self.message,
            'total_files': self.total_files,
            'total_directories': self.total_directories,
            'total_size': self.total_size,
            'has_rhoso_tests': self.has_rhoso_tests,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f'<Job {self.id} - {self.filename} ({self.status})>'
