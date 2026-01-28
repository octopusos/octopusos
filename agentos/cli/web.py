"""
Web UI Command - Launch WebUI control surface

agentos web [--host HOST] [--port PORT]
"""

import click
import logging


@click.command(name="web")
@click.option(
    "--host",
    default="127.0.0.1",
    help="Host to bind to (default: 127.0.0.1)",
    show_default=True,
)
@click.option(
    "--port",
    default=8080,
    type=int,
    help="Port to bind to (default: 8080)",
    show_default=True,
)
@click.option(
    "--reload",
    is_flag=True,
    help="Enable auto-reload (development mode)",
)
@click.option(
    "--log-level",
    default="info",
    type=click.Choice(["debug", "info", "warning", "error"]),
    help="Log level",
    show_default=True,
)
def web_cmd(host: str, port: int, reload: bool, log_level: str):
    """
    Launch AgentOS WebUI Control Surface

    The WebUI provides a web-based interface for:
    - Chat: Quick interventions and interactions
    - Control: Overview, sessions, logs, instances
    - Agent: Skills and memory management
    - Settings: Configuration and debug options

    Example:
        agentos web
        agentos web --port 8888
        agentos web --host 0.0.0.0 --port 8080
        agentos web --reload  # Development mode with auto-reload
    """
    try:
        import uvicorn
    except ImportError:
        click.secho(
            "Error: uvicorn is not installed. Install it with: pip install uvicorn",
            fg="red",
        )
        return 1

    # Setup logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger = logging.getLogger(__name__)

    # Print startup message
    click.secho("\n🚀 AgentOS WebUI v0.3.0 - Control Surface\n", fg="blue", bold=True)
    click.secho(f"   Host:     {host}", fg="cyan")
    click.secho(f"   Port:     {port}", fg="cyan")
    click.secho(f"   URL:      http://{host}:{port}", fg="green", bold=True)
    click.secho(f"   Reload:   {'Enabled' if reload else 'Disabled'}", fg="cyan")
    click.secho(f"   Log:      {log_level.upper()}\n", fg="cyan")

    if host == "0.0.0.0":
        click.secho("⚠️  Warning: Binding to 0.0.0.0 makes the WebUI accessible from network", fg="yellow")
        click.secho("   Make sure this is intended for your security context.\n", fg="yellow")

    click.secho("Press Ctrl+C to stop\n", fg="white", dim=True)

    # Run uvicorn
    try:
        uvicorn.run(
            "agentos.webui.app:app",
            host=host,
            port=port,
            reload=reload,
            log_level=log_level,
        )
    except KeyboardInterrupt:
        click.secho("\n\n👋 AgentOS WebUI stopped", fg="blue")
    except Exception as e:
        logger.error(f"Failed to start WebUI: {e}", exc_info=True)
        click.secho(f"\n❌ Error: {e}", fg="red")
        return 1

    return 0
