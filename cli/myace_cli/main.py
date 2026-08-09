"""MyACE CLI entrypoint — Typer application with subcommands."""

from pathlib import Path

import typer
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from myace_cli.auth import AuthManager
from myace_cli.scanner import export_to_collection, scan_directory
from myace_cli.sync import SyncEngine

app = typer.Typer(
    name="myace",
    help="MyACE — My Agentic Coding Environment CLI",
    add_completion=False,
)
console = Console()
auth_manager = AuthManager()
sync_engine = SyncEngine()


@app.callback()
def callback():
    """MyACE CLI — Sync agentic coding profiles to your local machine."""


@app.command()
def login(
    server: str = typer.Option(
        ..., "--server", "-s",
        help="MyACE API server URL (e.g., https://api.myace.localhost)",
    ),
    token: str = typer.Option(
        ..., "--token", "-t",
        help="API token generated from the MyACE web UI",
    ),
):
    """Authenticate with the MyACE server and store credentials locally."""
    try:
        auth_manager.store_credentials(server, token)
        rprint("[green]✓[/green] Credentials stored successfully.")
        rprint(f"   Server: [bold]{server}[/bold]")
        rprint(f"   Token:  [dim]{token[:12]}...[/dim]")
    except Exception as e:
        rprint(f"[red]✗[/red] Failed to store credentials: {e}")
        raise typer.Exit(1)


@app.command()
def logout():
    """Remove stored credentials from the local machine."""
    creds_path = auth_manager.credentials_path
    if creds_path.exists():
        creds_path.unlink()
        rprint("[green]✓[/green] Credentials removed.")
    else:
        rprint("[yellow]![/yellow] No credentials found.")


@app.command()
def status():
    """Show current authentication status and server info."""
    creds = auth_manager.load_credentials()
    if creds:
        rprint(Panel(
            f"[bold]Server:[/bold] {creds['server']}\n"
            f"[bold]Token:[/bold]  [dim]{creds['token'][:12]}...[/dim]\n"
            f"[bold]Config:[/bold] {auth_manager.credentials_path}",
            title="Authenticated",
            border_style="green",
        ))
    else:
        rprint("[yellow]Not authenticated.[/yellow] Run [bold]myace login[/bold] first.")


@app.command()
def pull(
    profile: str = typer.Option(
        ..., "--profile", "-p",
        help="Profile name or ID to pull",
    ),
    target: str = typer.Option(
        ..., "--target", "-t",
        help="Target framework (e.g., opencode, claude-code, cursor)",
    ),
    path: Path | None = typer.Option(
        None, "--path", "-o",
        help="Output directory (defaults to target-specific location)",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n",
        help="Preview files without writing them",
    ),
    force: bool = typer.Option(
        False, "--force", "-f",
        help="Overwrite existing files without confirmation",
    ),
):
    """Fetch a compiled profile from the server and write files locally."""
    creds = auth_manager.load_credentials()
    if not creds:
        rprint("[red]✗[/red] Not authenticated. Run [bold]myace login[/bold] first.")
        raise typer.Exit(1)

    try:
        result = sync_engine.pull_profile(
            server=creds["server"],
            token=creds["token"],
            profile_name=profile,
            target=target,
        )
    except Exception as e:
        rprint(f"[red]✗[/red] Failed to pull profile: {e}")
        raise typer.Exit(1)

    if not result or "files" not in result:
        rprint("[red]✗[/red] No files returned from server.")
        raise typer.Exit(1)

    files = result["files"]
    rprint(f"\n[bold]Profile:[/bold] {result.get('profile_name', profile)}")
    rprint(f"[bold]Target:[/bold]  {target}")
    rprint(f"[bold]Artifacts:[/bold] {result.get('artifact_count', 0)}")
    rprint(f"[bold]Files:[/bold]    {len(files)}\n")

    # Display file table
    table = Table(show_header=True, header_style="bold")
    table.add_column("File", style="cyan")
    table.add_column("Size", justify="right")
    table.add_column("Action", style="yellow")

    for filename, content in files.items():
        size = len(content)
        size_str = f"{size} chars" if size < 1000 else f"{size / 1000:.1f} KB"
        table.add_row(filename, size_str, "write" if not dry_run else "dry-run")

    console.print(table)

    if dry_run:
        rprint("\n[yellow]Dry run complete. No files were written.[/yellow]")
        return

    # Determine output path
    output_path = path or _default_target_path(target)
    rprint(f"\nOutput directory: [bold]{output_path}[/bold]")

    if not output_path.exists():
        output_path.mkdir(parents=True, exist_ok=True)

    # Write files
    written = 0
    skipped = 0
    for filename, content in files.items():
        # Prevent path traversal: reject filenames with path separators or
        # parent-dir references. The server's compile response is derived from
        # user-controlled artifact names, so a malicious/compromised server
        # could return a filename like '../../.bashrc'.
        if "/" in filename or "\\" in filename or ".." in filename:
            rprint(f"  [red]Skipping unsafe filename: {filename}[/red]")
            skipped += 1
            continue
        file_path = output_path / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)

        if file_path.exists() and not force:
            overwrite = typer.confirm(
                f"  Overwrite {filename}?",
                default=False,
            )
            if not overwrite:
                skipped += 1
                continue

        file_path.write_text(content)
        written += 1

    rprint(f"\n[green]✓[/green] {written} files written, {skipped} skipped.")
    rprint(f"   Location: [bold]{output_path}[/bold]")


@app.command()
def serve(
    port: int = typer.Option(
        8765, "--port", "-p",
        help="Local port to listen on (loopback-only)",
    ),
):
    """Run a local companion server so the web UI can scan this machine.

    Requires `myace login` first — only the server you're logged into is
    ever allowed to talk to it, and it binds to 127.0.0.1 only.
    """
    creds = auth_manager.load_credentials()
    if not creds:
        rprint("[red]✗[/red] Not authenticated. Run [bold]myace login[/bold] first.")
        raise typer.Exit(1)

    try:
        from myace_cli import local_server
    except ImportError:
        rprint("[red]✗[/red] Missing dependencies for the local server.")
        rprint('   Install with: [bold]pip install "myace-cli[serve]"[/bold]')
        raise typer.Exit(1)

    rprint(f"[green]✓[/green] Starting local companion server on [bold]http://127.0.0.1:{port}[/bold]")
    rprint(f"   Allowed origin: [bold]{creds['server']}[/bold]")
    rprint("   Open the Import page in your browser to scan this machine. Ctrl+C to stop.\n")
    local_server.run(allowed_origin=creds["server"], port=port)


@app.command()
def list_profiles():
    """List available profiles from the server."""
    creds = auth_manager.load_credentials()
    if not creds:
        rprint("[red]✗[/red] Not authenticated. Run [bold]myace login[/bold] first.")
        raise typer.Exit(1)

    try:
        profiles = sync_engine.list_profiles(
            server=creds["server"],
            token=creds["token"],
        )
    except Exception as e:
        rprint(f"[red]✗[/red] Failed to list profiles: {e}")
        raise typer.Exit(1)

    if not profiles:
        rprint("[yellow]No profiles found.[/yellow]")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("Name", style="cyan")
    table.add_column("ID", style="dim")
    table.add_column("Collections", justify="right")
    table.add_column("Public", justify="center")

    for profile in profiles:
        table.add_row(
            profile.get("name", "?"),
            str(profile.get("id", "?"))[:8] + "...",
            str(len(profile.get("additional_collection_ids", [])) + 1),
            "✓" if profile.get("is_public") else "—",
        )

    console.print(table)


@app.command(name="import")
def import_cmd(
    path: str = typer.Option(
        ..., "--path", "-p",
        help="Path to local config directory (e.g., ~/.config/opencode)",
    ),
    name: str = typer.Option(
        "imported-config", "--name", "-n",
        help="Name for the imported collection",
    ),
    output: Path | None = typer.Option(
        None, "--output", "-o",
        help="Output directory for the canonical collection (default: ./<name>)",
    ),
    push: bool = typer.Option(
        False, "--push",
        help="Push the collection to the MyACE server after exporting",
    ),
):
    """Scan a local config directory and convert it to canonical artifacts."""
    try:
        artifacts = scan_directory(path)
    except FileNotFoundError as e:
        rprint(f"[red]✗[/red] {e}")
        raise typer.Exit(1)

    if not artifacts:
        rprint("[yellow]![/yellow] No artifacts found in the specified directory.")
        return

    output_dir = output or Path.cwd() / name
    export_to_collection(artifacts, output_dir, collection_name=name)

    # Summary table
    table = Table(show_header=True, header_style="bold")
    table.add_column("Type", style="cyan")
    table.add_column("Count", justify="right")

    counts: dict[str, int] = {}
    for a in artifacts:
        counts[a["artifact_type"]] = counts.get(a["artifact_type"], 0) + 1

    for atype, count in sorted(counts.items()):
        table.add_row(atype, str(count))

    rprint(f"\n[green]✓[/green] Scanned [bold]{path}[/bold]")
    rprint(f"   Found [bold]{len(artifacts)}[/bold] artifacts")
    rprint(f"   Exported to [bold]{output_dir}[/bold]")
    console.print(table)

    # Show sample files
    rprint("\n[dim]Generated files:[/dim]")
    for f in sorted(output_dir.rglob("*.md")):
        if f.name != "README.md":
            rprint(f"  [dim]{f.relative_to(output_dir)}[/dim]")

    if push:
        creds = auth_manager.load_credentials()
        if not creds:
            rprint("[red]✗[/red] Not authenticated. Run [bold]myace login[/bold] first.")
            raise typer.Exit(1)

        import httpx
        url = f"{creds['server']}/api/v1/collections/import?owner_id={creds.get('user_id', '')}"
        headers = {
            "Authorization": f"Bearer {creds['token']}",
            "Content-Type": "application/json",
        }
        payload = {
            "collection_name": name,
            "collection_description": f"Imported from {path}",
            "collection_type": "base",
            "visibility": "private",
            "artifacts": artifacts,
        }

        try:
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                result = resp.json()
                rprint(
                    f"\n[green]✓[/green] Pushed to server: "
                    f"collection [bold]{result['collection_name']}[/bold]"
                )
                rprint(f"   Collection ID: {result['collection_id']}")
                rprint(f"   Artifacts imported: {result['artifacts_imported']}")
        except httpx.HTTPStatusError as e:
            rprint(f"[red]✗[/red] Failed to push: {e.response.status_code} {e.response.text}")
        except httpx.ConnectError:
            rprint(f"[red]✗[/red] Could not connect to {creds['server']}")


def _default_target_path(target: str) -> Path:
    """Return the default output path for a given target framework."""
    home = Path.home()
    target_paths = {
        "opencode": home / ".opencode",
        "claude-code": home / ".claude",
        "claude": home / ".claude",
        "cursor": home / ".cursor",
    }
    return target_paths.get(target, Path.cwd() / target)


if __name__ == "__main__":
    app()
