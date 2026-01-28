"""Doctor command - System health check without heavy dependencies"""

import sys
import click
from pathlib import Path


@click.command()
@click.option("--verbose", "-v", is_flag=True, help="Show detailed information")
def doctor(verbose):
    """Run system health check (no configuration required)

    This command verifies basic AgentOS functionality without requiring
    providers or adapters to be configured.
    """
    from agentos import __version__

    click.echo("🔍 AgentOS System Check")
    click.echo("=" * 50)
    click.echo()

    # Check 1: Python version
    py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    click.echo(f"✓ Python: {py_version}")

    # Check 2: AgentOS version
    click.echo(f"✓ AgentOS: {__version__}")

    # Check 3: Core modules
    try:
        from agentos.config import load_settings
        click.echo("✓ Config module: OK")
    except ImportError as e:
        click.echo(f"✗ Config module: FAIL - {e}")
        sys.exit(1)

    try:
        from agentos.store import get_db
        click.echo("✓ Store module: OK")
    except ImportError as e:
        click.echo(f"✗ Store module: FAIL - {e}")
        sys.exit(1)

    # Check 4: Database
    try:
        from agentos.store import get_db
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' LIMIT 1")
        result = cursor.fetchone()
        conn.close()

        if result:
            click.echo("✓ Database: Initialized")
        else:
            click.echo("⚠ Database: Empty (run 'agentos init')")
    except FileNotFoundError:
        click.echo("⚠ Database: Not found (run 'agentos init')")
    except Exception as e:
        if verbose:
            click.echo(f"⚠ Database: Error - {e}")
        else:
            click.echo("⚠ Database: Error (use --verbose for details)")

    # Check 5: Configuration
    try:
        from agentos.config import load_settings
        settings = load_settings()
        click.echo(f"✓ Settings: Loaded (mode={settings.run_mode})")
    except Exception as e:
        if verbose:
            click.echo(f"⚠ Settings: {e}")
        else:
            click.echo("⚠ Settings: Using defaults")

    # Check 6: WebUI module (check without loading heavy app)
    webui_path = Path(__file__).parent.parent / "webui" / "app.py"
    if webui_path.exists():
        click.echo("✓ WebUI: Available (code present)")
    else:
        click.echo("⚠ WebUI: Module not found")

    # Check 7: CLI module (check without loading)
    cli_path = Path(__file__).parent / "interactive.py"
    if cli_path.exists():
        click.echo("✓ Interactive CLI: Available (code present)")
    else:
        click.echo("⚠ Interactive CLI: Module not found")

    click.echo()
    click.echo("=" * 50)
    click.echo()
    click.echo("✅ Core system: OK")
    click.echo()
    click.echo("💡 Note: Provider and adapter checks are skipped in basic mode.")
    click.echo("   No network calls or heavy modules are loaded.")
    click.echo()
    click.echo("Next steps:")
    click.echo("  • Initialize database: agentos init")
    click.echo("  • Start WebUI: agentos --web")
    click.echo("  • Interactive CLI: agentos")
    click.echo()

    if verbose:
        click.echo("ℹ️  Verbose mode: Additional checks (providers, adapters) can be added")
        click.echo("   in future versions with --full flag.")
        click.echo()
