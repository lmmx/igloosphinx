# src/igloosphinx/cli.py

from __future__ import annotations

import sys
import click
from .inventory import Inventory


@click.command()
@click.argument("package_name", type=str)
@click.option(
    "--format",
    "-f",
    "output_format",
    default="table",
    help="Output format: table, csv, or json.",
)
def main(package_name: str, output_format: str) -> None:
    """
    Command-line interface for igloosphinx.
    Retrieves `objects.inv` data for a PACKAGE_NAME, then outputs it in the requested format.
    """
    inventory = Inventory(package_name=package_name)
    try:
        df = inventory.fetch_inventory()
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    if output_format == "csv":
        click.echo(df.write_csv())
    elif output_format == "json":
        click.echo(df.write_json())
    else:
        # Simple table output:
        # For a more user-friendly table, consider textual, rich, or tabulate
        click.echo(df)
