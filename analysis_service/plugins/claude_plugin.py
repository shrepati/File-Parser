"""
Claude AI Plugin
Implements test failure analysis using Anthropic's Claude API
"""

from typing import AsyncIterator, Dict, List, Union
import logging
import anthropic

from analysis_service.plugins.base import (
    AIBackendPlugin,
    AnalysisContext,
    AnalysisResult
)

logger = logging.getLogger(__name__)


class ClaudePlugin(AIBackendPlugin):
    """Anthropic Claude AI backend plugin"""

    def __init__(self):
        super().__init__()
        self.client = None
        self.api_key = None
        self.model = "claude-3-5-sonnet-20241022"  # Latest Claude model

    @property
    def name(self) -> str:
        return "claude"

    @property
    def display_name(self) -> str:
        return "Anthropic Claude 3.5 Sonnet"

    @property
    def supports_streaming(self) -> bool:
        return True

    async def initialize(self, config: Dict) -> None:
        """
        Initialize Claude plugin with API key

        Args:
            config: Configuration with 'api_key' field
        """
        self.api_key = config.get('api_key')

        if not self.api_key:
            logger.warning("Claude API key not provided")
            self.initialized = False
            return

        try:
            self.client = anthropic.AsyncAnthropic(api_key=self.api_key)
            self.initialized = True
            logger.info("Claude plugin initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Claude plugin: {e}")
            self.initialized = False
            raise

    def analyze_failures(
        self,
        context: AnalysisContext,
        stream: bool = False
    ) -> Union[AsyncIterator[str], AnalysisResult]:
        """
        Analyze test failures using Claude

        Args:
            context: Analysis context with failures and logs
            stream: Whether to stream response

        Returns:
            AsyncIterator[str] if streaming, AnalysisResult (coroutine) otherwise
        """
        if not self.initialized:
            raise RuntimeError("Claude plugin not initialized")

        # Build system prompt
        system_prompt = self._build_system_prompt(context)
        failures_text = self._format_failures_for_prompt(context.test_failures)

        # Add must-gather context if available
        mustgather_text = ""
        if context.log_excerpts:
            mustgather_text = "\n\nRelated Must-Gather Logs:\n"
            for i, excerpt in enumerate(context.log_excerpts[:5], 1):
                mustgather_text += f"\n{i}. File: {excerpt.get('file', 'Unknown')}\n"
                mustgather_text += f"   Context:\n{excerpt.get('context', 'No context')}\n"

        user_prompt = f"{failures_text}{mustgather_text}\n\nProvide a detailed analysis with:\n1. Summary of failure patterns\n2. Root cause analysis for each failure\n3. Correlated log insights\n4. Specific solutions"

        # Return async generator for streaming, coroutine for non-streaming
        if stream:
            return self._stream_analysis(system_prompt, user_prompt)
        else:
            return self._complete_analysis(system_prompt, user_prompt)

    async def _stream_analysis(self, system_prompt: str, user_prompt: str) -> AsyncIterator[str]:
        """Stream analysis response"""
        try:
            async with self.client.messages.stream(
                model=self.model,
                max_tokens=4096,
                temperature=0.7,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            ) as stream:
                async for text in stream.text_stream:
                    yield text

        except Exception as e:
            logger.error(f"Claude streaming failed: {e}")
            yield f"\n\n[Error: {str(e)}]"

    async def _complete_analysis(self, system_prompt: str, user_prompt: str) -> AnalysisResult:
        """Complete analysis response"""
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                temperature=0.7,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )

            # Extract text from response
            analysis_text = ""
            for block in response.content:
                if block.type == "text":
                    analysis_text += block.text

            # Parse response into structured format
            result = AnalysisResult(
                summary=self._extract_section(analysis_text, "Summary", "Root Cause"),
                failure_insights=self._parse_failure_insights(analysis_text),
                suggested_solutions=self._parse_solutions(analysis_text),
                correlated_logs=self._parse_correlated_logs(analysis_text),
                confidence=0.90  # Claude generally has high confidence
            )

            return result

        except Exception as e:
            logger.error(f"Claude analysis failed: {e}")
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
            raise RuntimeError("Claude plugin not initialized")

        # Build system prompt with context
        system_prompt = self._build_system_prompt(context)

        # Build message history in Claude format
        messages = []

        # Add conversation history
        for msg in history:
            role = msg.get('role')
            content = msg.get('content', '')

            if role in ['user', 'assistant']:
                messages.append({
                    "role": role,
                    "content": content
                })

        # Add current message
        messages.append({
            "role": "user",
            "content": message
        })

        # Return async generator for streaming, coroutine for non-streaming
        if stream:
            return self._stream_chat_response(system_prompt, messages)
        else:
            return self._complete_chat_response(system_prompt, messages)

    async def _complete_chat_response(self, system_prompt: str, messages: List[Dict]) -> str:
        """Complete (non-streaming) chat response"""
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                temperature=0.7,
                system=system_prompt,
                messages=messages
            )

            # Extract text from response
            response_text = ""
            for block in response.content:
                if block.type == "text":
                    response_text += block.text

            return response_text

        except Exception as e:
            logger.error(f"Claude chat failed: {e}")
            raise

    async def _stream_chat_response(self, system_prompt: str, messages: List[Dict]) -> AsyncIterator[str]:
        """Stream chat response"""
        try:
            async with self.client.messages.stream(
                model=self.model,
                max_tokens=2048,
                temperature=0.7,
                system=system_prompt,
                messages=messages
            ) as stream:
                async for text in stream.text_stream:
                    yield text

        except Exception as e:
            logger.error(f"Claude chat streaming failed: {e}")
            yield f"\n\n[Error: {str(e)}]"

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

        # Look for structured sections
        lines = text.split('\n')
        current_insight = {}

        for line in lines:
            line = line.strip()

            # Detect insight markers
            if any(marker in line.lower() for marker in ['test:', 'failure:', 'error:', 'issue:']):
                if current_insight:
                    insights.append(current_insight)
                current_insight = {'description': line}

            elif line.startswith(('-', '*', '•', '1.', '2.', '3.', '4.', '5.')):
                if current_insight:
                    insights.append(current_insight)
                current_insight = {'description': line.lstrip('-*•0123456789. ')}

            elif current_insight and line and not line.startswith('#'):
                # Continue current insight
                current_insight['description'] = current_insight.get('description', '') + ' ' + line

        if current_insight:
            insights.append(current_insight)

        return insights[:10]  # Limit to 10 insights

    def _parse_solutions(self, text: str) -> List[str]:
        """Parse suggested solutions"""
        solutions = []

        # Look for solution section
        solution_markers = ['solution', 'fix', 'recommendation', 'suggest', 'resolution']
        lines = text.split('\n')

        in_solution_section = False
        for line in lines:
            line_lower = line.lower().strip()

            # Check if we're entering solution section
            if any(marker in line_lower for marker in solution_markers):
                in_solution_section = True
                continue

            # Extract numbered or bulleted solutions
            if in_solution_section:
                if line.strip().startswith(('-', '*', '•')) or (len(line) > 0 and line[0].isdigit()):
                    solution = line.strip().lstrip('-*•0123456789. ')
                    if solution and len(solution) > 10:  # Filter out headers
                        solutions.append(solution)

        return solutions[:10]  # Limit to 10 solutions

    def _parse_correlated_logs(self, text: str) -> List[str]:
        """Parse correlated log references"""
        logs = []

        lines = text.split('\n')
        for line in lines:
            line_lower = line.lower()
            if 'log' in line_lower and any(keyword in line_lower for keyword in ['error', 'warn', 'fail', 'exception']):
                logs.append(line.strip())

        return logs[:5]  # Limit to 5 log references

    async def health_check(self) -> bool:
        """
        Check if Claude backend is healthy

        Returns:
            bool: True if healthy
        """
        if not self.initialized:
            return False

        try:
            # Simple test request
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=10,
                messages=[
                    {"role": "user", "content": "Test"}
                ]
            )
            return bool(response.content)

        except Exception as e:
            logger.error(f"Claude health check failed: {e}")
            return False
