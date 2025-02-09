# src/igloosphinx/inventory.py

from __future__ import annotations

import subprocess

import polars as pl
import requests
from pypi_docs_url import get_intersphinx_url
from sphinx.util.inventory import InventoryFile

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
        # 2. Download the objects.inv file
        raw_inv = self._download_inventory(objects_inv_url)
        # 3. Parse the inventory into a Polars DataFrame
        self._inventory_df = self._parse_inventory(
            raw_data=raw_inv, uri=objects_inv_url
        )
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
        # For now, simply demonstrate Polars usage:
        return pl.DataFrame({"from_v": [from_v], "to_v": [to_v]})

    def _discover_objects_inv(self) -> str:
        """
        Locates the objects.inv URL by invoking or simulating `pypi-docs-url`.
        Replace with your actual discovery logic or library call.
        """
        # Placeholder: Attempt a dummy subprocess call to pypi-docs-url, returning a mocked URL
        # In real usage, parse the stdout or otherwise gather the discovered URL
        try:
            url = get_intersphinx_url(self.package_name)
        except Exception as e:
            print(f"pypi-docs-url failed: {e}")
            # If pypi-docs-url is not installed, fallback to direct PyPI metadata approach or error
            url = self._fallback_metadata_lookup()
        return url

    def _fallback_metadata_lookup(self) -> str:
        """
        Fallback for discovering the objects.inv by hitting PyPI's JSON and applying heuristic logic.
        """
        # Minimal example, expand upon real logic as needed
        pypi_url = f"https://pypi.org/pypi/{self.package_name}/json"
        response = requests.get(pypi_url, timeout=10)
        if not response.ok:
            raise ValueError(f"Could not fetch PyPI metadata for {self.package_name}")

        data = response.json()
        project_urls = data["info"].get("project_urls", {})
        doc_url = project_urls.get("Documentation")
        if not doc_url:
            raise ValueError(
                f"No documentation URL found in PyPI metadata for {self.package_name}",
            )

        # Hypothetically guess the objects.inv location
        # You might need advanced heuristics, or user guidance
        if doc_url.endswith("/"):
            doc_url = doc_url[:-1]
        objects_inv_url = doc_url + "/objects.inv"
        return objects_inv_url

    def _download_inventory(self, url: str) -> bytes:
        """
        Downloads the raw objects.inv file from the discovered URL.
        """
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            raise ValueError(f"Failed to retrieve objects.inv at {url}")
        return resp.content

    def _parse_inventory(self, raw_data: bytes, uri: str) -> pl.DataFrame:
        """
        Parses the raw objects.inv data into a Polars DataFrame.
        This is a simplified placeholder. Real parsing requires
        handling Sphinx's zlib-compressed format and tokenisation.
        """
        try:
            inv = InventoryFile.loads(raw_data, uri=uri)
        except ValueError as exc:
            msg = f"Unknown or unsupported inventory version: {exc!r}"
            raise ValueError(msg) from exc
        df = inventory_to_polars_df(inv, lazy=self.lazy)

        # If lazy is desired, one might do:
        if self.lazy:
            # Convert to LazyFrame for subsequent transformations
            return df.lazy().collect()
        return df
