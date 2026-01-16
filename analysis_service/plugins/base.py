"""
Base AI Plugin Interface
Abstract base class for all AI backend plugins
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Dict, List, Optional, Union
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class AnalysisContext:
    """Context provided to AI for analysis"""
    test_failures: List[Dict]
    test_summary: Dict
    log_excerpts: List[Dict]
    must_gather_info: Optional[Dict] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'test_failures': self.test_failures,
            'test_summary': self.test_summary,
            'log_excerpts': self.log_excerpts,
            'must_gather_info': self.must_gather_info
        }


@dataclass
class AnalysisResult:
    """Result from AI analysis"""
    summary: str
    failure_insights: List[Dict]
    suggested_solutions: List[str]
    correlated_logs: List[str]
    confidence: float = 0.0

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'summary': self.summary,
            'failure_insights': self.failure_insights,
            'suggested_solutions': self.suggested_solutions,
            'correlated_logs': self.correlated_logs,
            'confidence': self.confidence
        }


class AIBackendPlugin(ABC):
    """Abstract base class for AI backend plugins"""

    def __init__(self):
        self.initialized = False
        self.config = {}

    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin identifier (e.g., 'gemini', 'claude', 'mcp')"""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name"""
        pass

    @property
    @abstractmethod
    def supports_streaming(self) -> bool:
        """Whether this backend supports streaming responses"""
        pass

    @abstractmethod
    async def initialize(self, config: Dict) -> None:
        """
        Initialize the plugin with configuration

        Args:
            config: Configuration dictionary with API keys and settings
        """
        pass

    @abstractmethod
    async def analyze_failures(
        self,
        context: AnalysisContext,
        stream: bool = False
    ) -> Union[AsyncIterator[str], AnalysisResult]:
        """
        Analyze test failures with context

        Args:
            context: Analysis context with failures and logs
            stream: If True, yield partial results; if False, return complete result

        Returns:
            AsyncIterator[str] if streaming, AnalysisResult if not
        """
        pass

    @abstractmethod
    async def chat(
        self,
        message: str,
        history: List[Dict],
        context: AnalysisContext,
        stream: bool = False
    ) -> Union[AsyncIterator[str], str]:
        """
        Interactive chat about test failures

        Args:
            message: User message
            history: Conversation history [{'role': 'user|assistant', 'content': '...'}]
            context: Analysis context
            stream: Whether to stream response

        Returns:
            AsyncIterator[str] if streaming, str if not
        """
        pass

    async def health_check(self) -> bool:
        """
        Check if backend is available and healthy

        Returns:
            bool: True if healthy, False otherwise
        """
        return self.initialized

    def _build_system_prompt(self, context: AnalysisContext) -> str:
        """
        Build system prompt for AI model

        Args:
            context: Analysis context

        Returns:
            str: System prompt
        """
        prompt = f"""You are an expert OpenStack test failure analyzer. You help developers understand why tempest tests fail.

Test Summary:
- Total Tests: {context.test_summary.get('total_tests', 0)}
- Failed: {context.test_summary.get('failed', 0)}
- Errors: {context.test_summary.get('errors', 0)}
- Skipped: {context.test_summary.get('skipped', 0)}

Your task is to:
1. Analyze the test failures and error messages
2. Correlate failures with must-gather logs when available
3. Identify root causes
4. Suggest concrete solutions

Be concise, technical, and actionable. Focus on the "why" and "how to fix"."""

        return prompt

    def _format_failures_for_prompt(self, failures: List[Dict], max_failures: int = 5) -> str:
        """
        Format test failures for AI prompt

        Args:
            failures: List of test failures
            max_failures: Maximum failures to include

        Returns:
            str: Formatted failures text
        """
        formatted = "Test Failures:\n\n"

        for i, failure in enumerate(failures[:max_failures], 1):
            formatted += f"{i}. Test: {failure.get('test_name', 'Unknown')}\n"
            formatted += f"   Class: {failure.get('class_name', 'Unknown')}\n"
            formatted += f"   Type: {failure.get('failure_type', 'failure')}\n"
            formatted += f"   Error: {failure.get('error_message', 'No message')}\n"

            traceback = failure.get('traceback', '')
            if traceback:
                # Limit traceback length
                traceback_lines = traceback.split('\n')[:10]
                formatted += f"   Traceback:\n"
                for line in traceback_lines:
                    formatted += f"     {line}\n"

            formatted += "\n"

        if len(failures) > max_failures:
            formatted += f"\n... and {len(failures) - max_failures} more failures\n"

        return formatted
