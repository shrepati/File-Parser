"""
Gemini AI Plugin
Implements test failure analysis using Google's Gemini API (New google-genai package)
"""

from typing import AsyncIterator, Dict, List, Union
import logging
from google import genai

from analysis_service.plugins.base import (
    AIBackendPlugin,
    AnalysisContext,
    AnalysisResult
)

logger = logging.getLogger(__name__)


class GeminiPlugin(AIBackendPlugin):
    """Google Gemini AI backend plugin"""

    def __init__(self):
        super().__init__()
        self.client = None
        self.api_key = None
        self.model_name = "gemini-2.0-flash-exp"  # Latest fast model

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def display_name(self) -> str:
        return "Google Gemini 2.0 Flash"

    @property
    def supports_streaming(self) -> bool:
        return True

    async def initialize(self, config: Dict) -> None:
        """
        Initialize Gemini plugin with API key

        Args:
            config: Configuration with 'api_key' field
        """
        self.api_key = config.get('api_key')

        if not self.api_key:
            logger.warning("Gemini API key not provided")
            self.initialized = False
            return

        try:
            # Initialize the new Gemini client
            self.client = genai.Client(api_key=self.api_key)

            self.initialized = True
            logger.info("Gemini plugin initialized successfully with new google-genai package")

        except Exception as e:
            logger.error(f"Failed to initialize Gemini plugin: {e}")
            self.initialized = False
            raise

    def analyze_failures(
        self,
        context: AnalysisContext,
        stream: bool = False
    ) -> Union[AsyncIterator[str], AnalysisResult]:
        """
        Analyze test failures using Gemini

        Args:
            context: Analysis context with failures and logs
            stream: Whether to stream response

        Returns:
            AsyncIterator[str] if streaming, AnalysisResult (coroutine) otherwise
        """
        if not self.initialized:
            raise RuntimeError("Gemini plugin not initialized")

        # Build prompt
        full_prompt = self._build_full_prompt(context)

        # Return the appropriate generator or coroutine
        if stream:
            # Return async generator directly
            return self._stream_analysis(full_prompt)
        else:
            # Return coroutine (will be awaited by caller)
            return self._complete_analysis(full_prompt)

    def _build_full_prompt(self, context: AnalysisContext) -> str:
        """Build the full analysis prompt"""
        system_prompt = self._build_system_prompt(context)
        failures_text = self._format_failures_for_prompt(context.test_failures)

        # Add must-gather context if available
        mustgather_text = ""
        if context.log_excerpts:
            mustgather_text = "\n\nRelated Must-Gather Logs:\n"
            for i, excerpt in enumerate(context.log_excerpts[:5], 1):
                mustgather_text += f"\n{i}. File: {excerpt.get('file', 'Unknown')}\n"
                mustgather_text += f"   Context:\n{excerpt.get('context', 'No context')}\n"

        return f"{system_prompt}\n\n{failures_text}{mustgather_text}\n\nProvide a detailed analysis with:\n1. Summary of failure patterns\n2. Root cause analysis for each failure\n3. Correlated log insights\n4. Specific solutions"

    async def _stream_analysis(self, prompt: str) -> AsyncIterator[str]:
        """Stream analysis response as async generator"""
        try:
            # Use new API streaming - await the coroutine first
            stream = await self.client.aio.models.generate_content_stream(
                model=self.model_name,
                contents=prompt
            )

            async for chunk in stream:
                if chunk.text:
                    yield chunk.text

        except Exception as e:
            logger.error(f"Gemini streaming failed: {e}")
            yield f"\n\n[Error: {str(e)}]"

    async def _complete_analysis(self, prompt: str) -> AnalysisResult:
        """Complete analysis response"""
        try:
            # Use new API non-streaming
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=prompt
            )

            # Parse response into structured format
            analysis_text = response.text

            # Simple parsing - in production, you'd use more sophisticated extraction
            result = AnalysisResult(
                summary=self._extract_section(analysis_text, "Summary", "Root Cause"),
                failure_insights=self._parse_failure_insights(analysis_text),
                suggested_solutions=self._parse_solutions(analysis_text),
                correlated_logs=self._parse_correlated_logs(analysis_text),
                confidence=0.85  # Could be enhanced with confidence scoring
            )

            return result

        except Exception as e:
            logger.error(f"Gemini analysis failed: {e}")
            raise

    def chat(
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
            history: Conversation history
            context: Analysis context
            stream: Whether to stream response

        Returns:
            AsyncIterator[str] if streaming, str (coroutine) otherwise
        """
        if not self.initialized:
            raise RuntimeError("Gemini plugin not initialized")

        # For streaming, return the generator wrapper
        # For non-streaming, return the coroutine
        if stream:
            return self._chat_stream_wrapper(message, history, context)
        else:
            return self._chat_complete_wrapper(message, history, context)

    async def _chat_stream_wrapper(self, message: str, history: List[Dict], context: AnalysisContext) -> AsyncIterator[str]:
        """Wrapper to set up chat and stream response"""
        chat_session = await self._setup_chat_session(context, history)
        async for chunk in self._stream_chat_response(chat_session, message):
            yield chunk

    async def _chat_complete_wrapper(self, message: str, history: List[Dict], context: AnalysisContext) -> str:
        """Wrapper to set up chat and get complete response"""
        chat_session = await self._setup_chat_session(context, history)
        return await self._complete_chat_response(chat_session, message)

    async def _setup_chat_session(self, context: AnalysisContext, history: List[Dict]):
        """Set up chat session with context and history"""
        try:
            system_prompt = self._build_system_prompt(context)

            # Build chat history in new format
            chat_history = []

            # Add system context as first user message
            chat_history.append({
                'role': 'user',
                'parts': [{'text': system_prompt}]
            })
            chat_history.append({
                'role': 'model',
                'parts': [{'text': 'I understand. I will analyze test failures based on this context.'}]
            })

            # Add conversation history
            for msg in history:
                role = msg.get('role')
                content = msg.get('content', '')

                if role == 'user':
                    chat_history.append({
                        'role': 'user',
                        'parts': [{'text': content}]
                    })
                elif role == 'assistant':
                    chat_history.append({
                        'role': 'model',
                        'parts': [{'text': content}]
                    })

            return chat_history

        except Exception as e:
            logger.error(f"Gemini chat setup failed: {e}")
            raise

    async def _stream_chat_response(self, chat_history, message: str) -> AsyncIterator[str]:
        """Stream chat response as async generator"""
        try:
            # Add current message to history
            chat_history.append({
                'role': 'user',
                'parts': [{'text': message}]
            })

            # Use new API streaming with chat history - await the coroutine first
            stream = await self.client.aio.models.generate_content_stream(
                model=self.model_name,
                contents=chat_history
            )

            async for chunk in stream:
                if chunk.text:
                    yield chunk.text

        except Exception as e:
            logger.error(f"Gemini chat streaming failed: {e}")
            yield f"\n\n[Error: {str(e)}]"

    async def _complete_chat_response(self, chat_history, message: str) -> str:
        """Complete chat response"""
        try:
            # Add current message to history
            chat_history.append({
                'role': 'user',
                'parts': [{'text': message}]
            })

            # Use new API non-streaming with chat history
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=chat_history
            )
            return response.text
        except Exception as e:
            logger.error(f"Gemini chat failed: {e}")
            raise

    def _extract_section(self, text: str, start_marker: str, end_marker: str = None) -> str:
        """Extract text between markers"""
        try:
            start_idx = text.lower().find(start_marker.lower())
            if start_idx == -1:
                return text[:500]  # Return first 500 chars as fallback

            if end_marker:
                end_idx = text.lower().find(end_marker.lower(), start_idx + len(start_marker))
                if end_idx != -1:
                    return text[start_idx:end_idx].strip()

            return text[start_idx:start_idx + 1000].strip()

        except Exception:
            return text[:500]

    def _parse_failure_insights(self, text: str) -> List[Dict]:
        """Parse failure insights from response"""
        insights = []

        # Simple line-based parsing
        lines = text.split('\n')
        current_insight = {}

        for line in lines:
            line = line.strip()
            if line.startswith('Test:') or line.startswith('-'):
                if current_insight:
                    insights.append(current_insight)
                current_insight = {'description': line}
            elif current_insight and line:
                current_insight['description'] = current_insight.get('description', '') + ' ' + line

        if current_insight:
            insights.append(current_insight)

        return insights[:10]  # Limit to 10 insights

    def _parse_solutions(self, text: str) -> List[str]:
        """Parse suggested solutions"""
        solutions = []

        # Look for solution section
        solution_markers = ['solution', 'fix', 'recommendation', 'suggest']
        lines = text.split('\n')

        in_solution_section = False
        for line in lines:
            line_lower = line.lower().strip()

            # Check if we're entering solution section
            if any(marker in line_lower for marker in solution_markers):
                in_solution_section = True
                continue

            # Extract numbered or bulleted solutions
            if in_solution_section and (line.strip().startswith(('-', '*', '•')) or
                                       (len(line) > 0 and line[0].isdigit())):
                solution = line.strip().lstrip('-*•0123456789. ')
                if solution:
                    solutions.append(solution)

        return solutions[:10]  # Limit to 10 solutions

    def _parse_correlated_logs(self, text: str) -> List[str]:
        """Parse correlated log references"""
        logs = []

        lines = text.split('\n')
        for line in lines:
            if 'log' in line.lower() and ('error' in line.lower() or 'warn' in line.lower()):
                logs.append(line.strip())

        return logs[:5]  # Limit to 5 log references

    async def health_check(self) -> bool:
        """
        Check if Gemini backend is healthy

        Returns:
            bool: True if healthy
        """
        if not self.initialized:
            return False

        try:
            # Simple test request with new API
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents="Test"
            )
            return bool(response.text)
        except Exception as e:
            logger.error(f"Gemini health check failed: {e}")
            return False
