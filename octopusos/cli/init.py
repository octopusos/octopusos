"""CLI init command"""

import click
from rich.console import Console

from octopusos.store import init_db

console = Console()


@click.command()
def init_cmd():
    """Initialize OctopusOS store"""
    try:
        db_path = init_db()
        console.print(f"✅ OctopusOS initialized at [green]{db_path}[/green]")
    except Exception as e:
        console.print(f"❌ [red]Initialization failed: {e}[/red]")
        raise click.Abort()
