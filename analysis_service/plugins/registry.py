"""
Plugin Registry
Manages AI backend plugin registration and discovery
"""

from typing import Dict, List, Optional
import logging

from analysis_service.plugins.base import AIBackendPlugin

logger = logging.getLogger(__name__)


class PluginRegistry:
    """Manages AI backend plugin registration and discovery"""

    def __init__(self):
        self._plugins: Dict[str, AIBackendPlugin] = {}

    def register(self, plugin: AIBackendPlugin) -> None:
        """
        Register a plugin

        Args:
            plugin: Plugin instance to register
        """
        logger.info(f"Registering plugin: {plugin.name}")
        self._plugins[plugin.name] = plugin

    def get(self, name: str) -> Optional[AIBackendPlugin]:
        """
        Get plugin by name

        Args:
            name: Plugin name

        Returns:
            Plugin instance or None if not found
        """
        return self._plugins.get(name)

    def list_available(self) -> List[Dict]:
        """
        List all registered plugins

        Returns:
            List of plugin info dictionaries
        """
        return [
            {
                'name': p.name,
                'display_name': p.display_name,
                'supports_streaming': p.supports_streaming,
                'initialized': p.initialized
            }
            for p in self._plugins.values()
        ]

    async def initialize_all(self, config: Dict) -> None:
        """
        Initialize all plugins

        Args:
            config: Configuration dictionary with plugin-specific configs
        """
        for plugin in self._plugins.values():
            plugin_config = config.get(plugin.name, {})
            try:
                await plugin.initialize(plugin_config)
                logger.info(f"Initialized plugin: {plugin.name}")
            except Exception as e:
                logger.error(f"Failed to initialize plugin {plugin.name}: {e}")

    def get_available_plugins(self) -> List[str]:
        """
        Get list of available plugin names

        Returns:
            List of plugin names
        """
        return list(self._plugins.keys())


# Global registry instance
registry = PluginRegistry()


def auto_discover_plugins():
    """
    Auto-discover and register all available plugins
    """
    logger.info("Auto-discovering AI plugins...")

    # Try to import and register Gemini plugin
    try:
        from analysis_service.plugins.gemini_plugin import GeminiPlugin
        registry.register(GeminiPlugin())
        logger.info("Registered Gemini plugin")
    except ImportError as e:
        logger.warning(f"Gemini plugin not available: {e}")
    except Exception as e:
        logger.error(f"Error registering Gemini plugin: {e}")

    # Try to import and register Claude plugin
    try:
        from analysis_service.plugins.claude_plugin import ClaudePlugin
        registry.register(ClaudePlugin())
        logger.info("Registered Claude plugin")
    except ImportError as e:
        logger.warning(f"Claude plugin not available: {e}")
    except Exception as e:
        logger.error(f"Error registering Claude plugin: {e}")

    # Try to import and register MCP plugin
    try:
        from analysis_service.plugins.mcp_plugin import MCPPlugin
        registry.register(MCPPlugin())
        logger.info("Registered MCP plugin")
    except ImportError as e:
        logger.warning(f"MCP plugin not available: {e}")
    except Exception as e:
        logger.error(f"Error registering MCP plugin: {e}")

    logger.info(f"Plugin discovery complete. Available plugins: {registry.get_available_plugins()}")


# Auto-discover plugins on module import
auto_discover_plugins()
