"""
MCP (Model Context Protocol) integration module

This module provides integration with MCP servers, allowing OctopusOS to
use tools from MCP-compliant servers alongside native Extensions.

Components:
- MCPConfigManager: Configuration loading and management
- MCPClient: Stdio-based MCP protocol client
- MCPAdapter: Converts MCP tools to ToolDescriptor format
- MCPHealthChecker: Health monitoring for MCP servers

Example:
    from octopusos.core.mcp import MCPConfigManager, MCPClient, MCPAdapter

    # Load configuration
    config_manager = MCPConfigManager()
    servers = config_manager.get_enabled_servers()

    # Connect to server
    client = MCPClient(servers[0])
    await client.connect()

    # List and adapt tools
    mcp_tools = await client.list_tools()
    adapter = MCPAdapter()
    for mcp_tool in mcp_tools:
        descriptor = adapter.mcp_tool_to_descriptor(
            server_id=servers[0].id,
            mcp_tool=mcp_tool,
            server_config=servers[0]
        )
"""

from octopusos.core.mcp.config import MCPConfigManager, MCPServerConfig
from octopusos.core.mcp.client import MCPClient, MCPClientError
from octopusos.core.mcp.adapter import MCPAdapter
from octopusos.core.mcp.health import MCPHealthChecker, HealthStatus

__all__ = [
    "MCPConfigManager",
    "MCPServerConfig",
    "MCPClient",
    "MCPClientError",
    "MCPAdapter",
    "MCPHealthChecker",
    "HealthStatus",
]
