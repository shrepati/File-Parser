"""
Analysis Models - Test analysis and AI conversation tracking
"""

from datetime import datetime
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Text, Float
from app.database import Base


class TestAnalysis(Base):
    """Stores test analysis results"""

    __tablename__ = 'test_analyses'

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(36), ForeignKey('jobs.id', ondelete='CASCADE'), nullable=False)

    # Test folder information
    test_folder = Column(String(255), nullable=False)  # e.g., rhoso-cert-cinder-s00-volumes

    # Test summary
    total_tests = Column(Integer, default=0)
    passed = Column(Integer, default=0)
    failed = Column(Integer, default=0)
    skipped = Column(Integer, default=0)
    errors = Column(Integer, default=0)
    duration = Column(Float, nullable=True)  # seconds

    # AI analysis metadata
    analyzed_at = Column(DateTime, default=datetime.utcnow)
    ai_backend = Column(String(50), nullable=True)  # 'gemini', 'claude', 'mcp'

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'job_id': self.job_id,
            'test_folder': self.test_folder,
            'total_tests': self.total_tests,
            'passed': self.passed,
            'failed': self.failed,
            'skipped': self.skipped,
            'errors': self.errors,
            'duration': self.duration,
            'analyzed_at': self.analyzed_at.isoformat() if self.analyzed_at else None,
            'ai_backend': self.ai_backend,
        }

    def __repr__(self):
        return f'<TestAnalysis {self.test_folder} - {self.failed} failures>'


class TestFailure(Base):
    """Stores individual test failures with AI analysis"""

    __tablename__ = 'test_failures'

    id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_id = Column(Integer, ForeignKey('test_analyses.id', ondelete='CASCADE'), nullable=False)

    # Test information
    test_name = Column(String(255), nullable=False)
    class_name = Column(String(255), nullable=False)
    error_message = Column(Text, nullable=True)
    traceback = Column(Text, nullable=True)
    failure_type = Column(String(50), nullable=True)  # 'failure', 'error', 'skip'

    # AI analysis results
    ai_summary = Column(Text, nullable=True)
    correlated_logs = Column(Text, nullable=True)  # JSON array of log file paths
    suggested_solutions = Column(Text, nullable=True)  # JSON array of suggestions

    def to_dict(self):
        """Convert to dictionary"""
        import json
        return {
            'id': self.id,
            'analysis_id': self.analysis_id,
            'test_name': self.test_name,
            'class_name': self.class_name,
            'error_message': self.error_message,
            'traceback': self.traceback,
            'failure_type': self.failure_type,
            'ai_summary': self.ai_summary,
            'correlated_logs': json.loads(self.correlated_logs) if self.correlated_logs else [],
            'suggested_solutions': json.loads(self.suggested_solutions) if self.suggested_solutions else [],
        }

    def __repr__(self):
        return f'<TestFailure {self.test_name}>'


class AIConversation(Base):
    """Stores AI chat history for test failures"""

    __tablename__ = 'ai_conversations'

    id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_id = Column(Integer, ForeignKey('test_analyses.id', ondelete='CASCADE'), nullable=False)

    message = Column(Text, nullable=False)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    timestamp = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'message': self.message,
            'role': self.role,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
        }

    def __repr__(self):
        return f'<AIConversation {self.role}: {self.message[:50]}...>'
