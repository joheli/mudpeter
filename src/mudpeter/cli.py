from pathlib import Path
from typing import Annotated
import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

from mudpeter.config import AppConfig
from mudpeter.pipeline import fetch_publications_from_pubmed, enrich_publications_with_fulltext
from mudpeter.db import make_sqlite_url, get_engine, init_db as _init_db, upsert_publications

from mudpeter.utils.export import export_fulltexts

console = Console()

app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="mudpeter: download publication metadata/fulltext and persist to a database.",
)


def _render_summary(n_total: int, n_with_fulltext: int) -> None:
    """ 
    This is a helper to output mudpeter results to the console
    """
    table = Table(title="Run summary")
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    table.add_row("Publications fetched", str(n_total))
    table.add_row("With full text", str(n_with_fulltext))
    console.print(table)


@app.command("run")
def run(
    config: Annotated[Path, typer.Option("--config", "-c", exists=True, dir_okay=False, readable=True, help="Path to TOML config file")],
    init_db: Annotated[bool, typer.Option("--init-db/--no-init-db", help="Create tables if needed")] = True, # this is probably not necessary for sqlite!
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Fetch/enrich but do not write to database")] = False,
) -> None:
    """
    Execute a full run: PubMed search -> fetch metadata -> optional fulltext -> persist.
    """
    try:
        cfg = AppConfig.from_toml(config)
    except Exception as e:
        console.print(f"[red]Config error:[/red] {e}")
        raise typer.Exit(code=2)

    db_url = make_sqlite_url(cfg.database.sqlite_path)  # type: ignore[arg-type]
    engine = get_engine(db_url, echo=cfg.database.echo)

    if init_db and not dry_run:
        _init_db(engine)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        t_fetch = progress.add_task("Fetching PubMed records", total=None)
        pubs = fetch_publications_from_pubmed(
            term=cfg.pubmed.term,
            email=cfg.pubmed.email,
            retmax=cfg.pubmed.retmax,
            batch_size=cfg.pubmed.batch_size,
            config=cfg # cfg is passed on to extract the optional keyword
        )
        progress.update(t_fetch, completed=1, total=1)

        if cfg.fulltext.enabled:
            t_enrich = progress.add_task("Enriching with full text", total=len(pubs))
            pubs = enrich_publications_with_fulltext(
                pubs,
                email_for_unpaywall=cfg.pubmed.email,
                enabled=cfg.fulltext.enabled,
                prefer_pmc=cfg.fulltext.prefer_pmc,
                use_pdf=cfg.fulltext.use_pdf,
                max_chars=cfg.fulltext.max_chars,
            )
            progress.update(t_enrich, completed=len(pubs))

    n_total = len(pubs)
    n_with_fulltext = sum(1 for p in pubs if p.full_text)
    _render_summary(n_total, n_with_fulltext)

    if dry_run:
        console.print("[yellow]Dry run:[/yellow] not writing to database.")
        raise typer.Exit(code=0)

    try:
        n = upsert_publications(engine, pubs)
    except Exception as e:
        console.print(f"[red]Database write failed:[/red] {e}")
        raise typer.Exit(code=1)

    console.print(f"[green]Done.[/green] Upserted {n} publication(s) into {db_url}.")


@app.command("validate-config")
def validate_config(config: Annotated[Path, typer.Argument(exists=True, dir_okay=False, readable=True)]) -> None:
    """Validate a TOML configuration file and print the parsed config."""
    try:
        cfg = AppConfig.from_toml(config)
    except Exception as e:
        console.print(f"[red]Invalid config:[/red] {e}")
        raise typer.Exit(code=2)
    console.print(cfg.model_dump())

@app.command("export")
def export(config: Annotated[Path, typer.Option("--config", "-c", exists=True, dir_okay=False, readable=True, help="Path to TOML config file")],
           export_directory: Annotated[Path, typer.Option("--export_directory", "-e", dir_okay=True, file_okay=False, help="Path to export directory")],
           keyword: Annotated[str | None, typer.Option("--keyword", "-k", help="Filter by keyword")] = None):
    """ 
    Export full-texts as text files from the database to a given root directory.
    If provided, only full text corresponding to a keyword are exported.
    """
    try:
        cfg = AppConfig.from_toml(config)
    except Exception as e:
        console.print(f"[red]Config error:[/red] {e}")
        raise typer.Exit(code=2)

    db_url = make_sqlite_url(cfg.database.sqlite_path)  # type: ignore[arg-type]
    engine = get_engine(db_url, echo=cfg.database.echo)
    
    try:
        export_fulltexts(export_directory, engine, keyword)
    except Exception as e:
        console.print(f"[red]Export error:[/red] {e}")
        raise typer.Exit(code=2)
    
def main() -> None:
    app()