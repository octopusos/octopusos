"""Top-level log commands for OctopusOS runtime."""

from __future__ import annotations

import click
import requests

from octopusos.daemon.service import get_or_create_control_token, read_status, tail_logs


def _control_logs(lines: int) -> str:
    status = read_status()
    if not status.running:
        return ""
    url = f"http://{status.host}:{status.port}/api/daemon/logs"
    headers = {"X-OctopusOS-Token": get_or_create_control_token()}
    try:
        resp = requests.get(url, headers=headers, timeout=1.5, params={"lines": lines})
        if not resp.ok:
            return ""
        return str(resp.json().get("content", ""))
    except requests.RequestException:
        return ""


@click.command(name="logs")
@click.option("--tail", is_flag=True, help="Show tail of daemon logs")
@click.option("--lines", default=100, type=int, help="Number of lines to show")
def logs_cmd(tail: bool, lines: int) -> None:
    """Show daemon logs (same source as `octopusos webui logs`)."""
    if not tail:
        raise click.UsageError("use --tail")

    content = _control_logs(lines=lines) or tail_logs(lines=lines)
    if not content:
        click.echo("no logs yet")
        return
    click.echo(content)
