"""
File Metadata Model - For search indexing
"""

from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, Index, Text
from app.database import Base


class FileMetadata(Base):
    """Stores file metadata for search and browsing"""

    __tablename__ = 'file_metadata'

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(36), ForeignKey('jobs.id', ondelete='CASCADE'), nullable=False)

    # File information
    name = Column(String(255), nullable=False)
    path = Column(Text, nullable=False)  # Absolute path on disk
    relative_path = Column(Text, nullable=False)  # Path relative to extraction root
    size = Column(Integer, nullable=True)  # bytes, None for directories
    extension = Column(String(50), nullable=True)

    # Flags
    is_directory = Column(Boolean, default=False)

    # Hierarchy
    parent_path = Column(Text, nullable=True)

    # Content preview for search (first 500 chars)
    content_preview = Column(Text, nullable=True)

    # Indexes for performance
    __table_args__ = (
        Index('idx_file_metadata_job', 'job_id'),
        Index('idx_file_metadata_name', 'name'),
        Index('idx_file_metadata_path', 'relative_path'),
        Index('idx_file_metadata_extension', 'extension'),
    )

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'path': self.relative_path,
            'size': self.size,
            'extension': self.extension,
            'is_directory': self.is_directory,
            'parent_path': self.parent_path,
        }

    def __repr__(self):
        return f'<FileMetadata {self.name} ({self.relative_path})>'
