"""
MCP (Model Context Protocol) Plugin
Integrates with MCP servers for test failure analysis
"""

from typing import AsyncIterator, Dict, List, Union, Optional
import logging
import aiohttp
import json

from analysis_service.plugins.base import (
    AIBackendPlugin,
    AnalysisContext,
    AnalysisResult
)

logger = logging.getLogger(__name__)


class MCPPlugin(AIBackendPlugin):
    """MCP Server integration plugin"""

    def __init__(self):
        super().__init__()
        self.server_url = None
        self.session = None

    @property
    def name(self) -> str:
        return "mcp"

    @property
    def display_name(self) -> str:
        return "MCP Server"

    @property
    def supports_streaming(self) -> bool:
        return True

    async def initialize(self, config: Dict) -> None:
        """
        Initialize MCP plugin with server URL

        Args:
            config: Configuration with 'server_url' field
        """
        self.server_url = config.get('server_url', 'http://localhost:9000')

        if not self.server_url:
            logger.warning("MCP server URL not provided")
            self.initialized = False
            return

        try:
            # Create aiohttp session
            self.session = aiohttp.ClientSession()

            # Test connection to MCP server
            async with self.session.get(f"{self.server_url}/health") as response:
                if response.status == 200:
                    self.initialized = True
                    logger.info(f"MCP plugin initialized successfully: {self.server_url}")
                else:
                    logger.warning(f"MCP server returned status {response.status}")
                    self.initialized = False

        except aiohttp.ClientError as e:
            logger.warning(f"MCP server not reachable at {self.server_url}: {e}")
            self.initialized = False
        except Exception as e:
            logger.error(f"Failed to initialize MCP plugin: {e}")
            self.initialized = False

    async def analyze_failures(
        self,
        context: AnalysisContext,
        stream: bool = False
    ) -> Union[AsyncIterator[str], AnalysisResult]:
        """
        Analyze test failures using MCP server

        Args:
            context: Analysis context with failures and logs
            stream: Whether to stream response

        Returns:
            AsyncIterator[str] if streaming, AnalysisResult otherwise
        """
        if not self.initialized:
            raise RuntimeError("MCP plugin not initialized")

        # Build request payload
        payload = {
            "action": "analyze_failures",
            "context": context.to_dict(),
            "stream": stream
        }

        try:
            if stream:
                return self._stream_analysis(payload)
            else:
                return await self._complete_analysis(payload)

        except Exception as e:
            logger.error(f"MCP analysis failed: {e}")
            raise

    async def _stream_analysis(self, payload: Dict) -> AsyncIterator[str]:
        """Stream analysis response from MCP server"""
        try:
            async with self.session.post(
                f"{self.server_url}/api/analyze",
                json=payload,
                headers={"Accept": "text/event-stream"}
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    yield f"[Error: MCP server returned {response.status}: {error_text}]"
                    return

                # Process Server-Sent Events
                async for line in response.content:
                    line = line.decode('utf-8').strip()

                    if line.startswith('data: '):
                        data = line[6:]  # Remove 'data: ' prefix

                        if data == '[DONE]':
                            break

                        try:
                            chunk = json.loads(data)
                            if 'text' in chunk:
                                yield chunk['text']
                        except json.JSONDecodeError:
                            # Plain text chunk
                            yield data

        except aiohttp.ClientError as e:
            logger.error(f"MCP streaming failed: {e}")
            yield f"\n\n[Error: {str(e)}]"
        except Exception as e:
            logger.error(f"MCP streaming error: {e}")
            yield f"\n\n[Error: {str(e)}]"

    async def _complete_analysis(self, payload: Dict) -> AnalysisResult:
        """Complete analysis response from MCP server"""
        try:
            async with self.session.post(
                f"{self.server_url}/api/analyze",
                json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(f"MCP server returned {response.status}: {error_text}")

                result_data = await response.json()

                # Convert MCP response to AnalysisResult
                result = AnalysisResult(
                    summary=result_data.get('summary', ''),
                    failure_insights=result_data.get('failure_insights', []),
                    suggested_solutions=result_data.get('suggested_solutions', []),
                    correlated_logs=result_data.get('correlated_logs', []),
                    confidence=result_data.get('confidence', 0.75)
                )

                return result

        except aiohttp.ClientError as e:
            logger.error(f"MCP analysis request failed: {e}")
            raise
        except Exception as e:
            logger.error(f"MCP analysis failed: {e}")
            raise

    async def chat(
        self,
        message: str,
        history: List[Dict],
        context: AnalysisContext,
        stream: bool = False
    ) -> Union[AsyncIterator[str], str]:
        """
        Interactive chat with MCP server

        Args:
            message: User message
            history: Conversation history
            context: Analysis context
            stream: Whether to stream response

        Returns:
            AsyncIterator[str] if streaming, str otherwise
        """
        if not self.initialized:
            raise RuntimeError("MCP plugin not initialized")

        # Build chat request payload
        payload = {
            "action": "chat",
            "message": message,
            "history": history,
            "context": context.to_dict(),
            "stream": stream
        }

        try:
            if stream:
                return self._stream_chat_response(payload)
            else:
                return await self._complete_chat_response(payload)

        except Exception as e:
            logger.error(f"MCP chat failed: {e}")
            raise

    async def _stream_chat_response(self, payload: Dict) -> AsyncIterator[str]:
        """Stream chat response from MCP server"""
        try:
            async with self.session.post(
                f"{self.server_url}/api/chat",
                json=payload,
                headers={"Accept": "text/event-stream"}
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    yield f"[Error: MCP server returned {response.status}: {error_text}]"
                    return

                # Process Server-Sent Events
                async for line in response.content:
                    line = line.decode('utf-8').strip()

                    if line.startswith('data: '):
                        data = line[6:]

                        if data == '[DONE]':
                            break

                        try:
                            chunk = json.loads(data)
                            if 'text' in chunk:
                                yield chunk['text']
                        except json.JSONDecodeError:
                            yield data

        except aiohttp.ClientError as e:
            logger.error(f"MCP chat streaming failed: {e}")
            yield f"\n\n[Error: {str(e)}]"
        except Exception as e:
            logger.error(f"MCP chat error: {e}")
            yield f"\n\n[Error: {str(e)}]"

    async def _complete_chat_response(self, payload: Dict) -> str:
        """Complete chat response from MCP server"""
        try:
            async with self.session.post(
                f"{self.server_url}/api/chat",
                json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(f"MCP server returned {response.status}: {error_text}")

                result = await response.json()
                return result.get('response', '')

        except aiohttp.ClientError as e:
            logger.error(f"MCP chat request failed: {e}")
            raise
        except Exception as e:
            logger.error(f"MCP chat failed: {e}")
            raise

    async def health_check(self) -> bool:
        """
        Check if MCP server is healthy

        Returns:
            bool: True if healthy
        """
        if not self.initialized or not self.session:
            return False

        try:
            async with self.session.get(
                f"{self.server_url}/health",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                return response.status == 200

        except Exception as e:
            logger.error(f"MCP health check failed: {e}")
            return False

    async def cleanup(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()
            self.session = None

    def __del__(self):
        """Ensure session is closed"""
        if self.session and not self.session.closed:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.cleanup())
                else:
                    loop.run_until_complete(self.cleanup())
            except Exception:
                pass
