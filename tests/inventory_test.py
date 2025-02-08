# tests/test_inventory.py

import polars as pl

from igloosphinx import Inventory


def test_inventory_fetch(monkeypatch):
    """
    Basic test for fetch_inventory. Mock network calls to ensure it returns
    an expected Polars DataFrame shape and columns.
    """

    def mock_discover_objects_inv(_self):
        return "mock://test-objects.inv"

    def mock_download_inventory(_self, url: str):
        return b"FAKE_INVENTORY_CONTENTS"

    monkeypatch.setattr(Inventory, "_discover_objects_inv", mock_discover_objects_inv)
    monkeypatch.setattr(Inventory, "_download_inventory", mock_download_inventory)

    inv = Inventory("example-package")
    df = inv.fetch_inventory()

    assert isinstance(df, pl.DataFrame)
    assert set(df.columns) == {"symbol_name", "symbol_type", "reference_url"}
