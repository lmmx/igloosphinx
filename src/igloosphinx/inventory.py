# src/igloosphinx/inventory.py

from __future__ import annotations

import polars as pl
import sphobjinv
from pypi_docs_url import get_intersphinx_url

from .convert import inventory_to_polars_df


class Inventory:
    """
    Provides functionality to retrieve and parse a package's `objects.inv`
    into a Polars DataFrame, using PyPI metadata to discover the documentation URL.
    """

    def __init__(
        self,
        package_name: str,
        version: str = "latest",
        lazy: bool = False,
    ) -> None:
        """
        Initialise the Inventory object.

        Args:
            package_name: The package name on PyPI.
            version: Optional version indicator for future expansions (e.g., specific docs version).
            lazy: Whether to allow lazy Polars operations (not all transformations may be supported).
        """
        self.package_name = package_name
        self.version = version
        self.lazy = lazy
        self._inventory_df: pl.DataFrame | None = None

    def fetch_inventory(self) -> pl.DataFrame:
        """
        Fetches and parses the `objects.inv` file for the specified package.
        Returns a Polars DataFrame with symbol data.
        """
        # 1. Discover the URL of the objects.inv via pypi-docs-url or direct PyPI metadata
        objects_inv_url = self._discover_objects_inv()
        # 2. Parse the inventory into a Polars DataFrame
        self._inventory_df = self._parse_inventory(url=objects_inv_url)
        return self._inventory_df

    def review_version_changes(
        self,
        from_v: str = "first",
        to_v: str = "latest",
    ) -> pl.DataFrame:
        """
        Compare documentation metadata across two versions.
        Currently a placeholder returning an empty DataFrame.
        Intended to be expanded upon for advanced comparisons.
        """
        return pl.DataFrame({"from_v": [from_v], "to_v": [to_v]})

    def _discover_objects_inv(self) -> str:
        """
        Locates the objects.inv URL by invoking or simulating `pypi-docs-url`.
        Replace with your actual discovery logic or library call.
        """
        try:
            url = get_intersphinx_url(self.package_name)
        except Exception as e:
            print(f"pypi-docs-url failed: {e}")
            raise SystemExit(1)
        return url

    def _parse_inventory(self, url: str) -> pl.DataFrame:
        """
        Parses the raw objects.inv data into a Polars DataFrame using sphobjinv.
        """
        try:
            inv = sphobjinv.Inventory(url=url)
        except sphobjinv.SphobjinvError as exc:
            msg = f"Unable to parse objects.inv: {exc!r}"
            raise ValueError(msg) from exc

        df = inventory_to_polars_df(inv, lazy=self.lazy)

        return df.lazy().collect() if self.lazy else df
