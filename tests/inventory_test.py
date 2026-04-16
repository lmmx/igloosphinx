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

    class MockSphInventory:
        def __init__(self, url):
            self.url = url

    def mock_inventory_to_df(_inv, lazy=False):
        return pl.DataFrame(
            {
                "symbol_name": ["foo"],
                "symbol_type": ["function"],
                "reference_url": ["https://example.com"],
            }
        )

    monkeypatch.setattr(Inventory, "_discover_objects_inv", mock_discover_objects_inv)
    monkeypatch.setattr("igloosphinx.inventory.sphobjinv.Inventory", MockSphInventory)
    monkeypatch.setattr(
        "igloosphinx.inventory.inventory_to_polars_df", mock_inventory_to_df
    )

    inv = Inventory("example-package")
    df = inv.fetch_inventory()

    assert isinstance(df, pl.DataFrame)
    assert set(df.columns) == {"symbol_name", "symbol_type", "reference_url"}
