import polars as pl
from sphinx.util.inventory import _Inventory


def inventory_to_polars_df(inv: _Inventory, lazy: bool = False) -> pl.DataFrame:
    """
    Convert a sphinx.util.inventory._Inventory instance
    into a Polars DataFrame with columns:
      - domain_role (e.g. 'py:class')
      - fullname     (e.g. 'polars.Catalog')
      - display_name (may be '-' if omitted)
      - project_name
      - project_version
      - uri
    """
    records = []
    for domain_role, obj_dict in inv.data.items():
        for fullname, item in obj_dict.items():
            records.append(
                {
                    "domain_role": domain_role,
                    "fullname": fullname,
                    "display_name": item.display_name,  # often '-'
                    "project_name": item.project_name,  # e.g. 'Polars'
                    "project_version": item.project_version,  # e.g. '' if not set
                    "uri": item.uri,  # doc reference, e.g. https://docs...
                }
            )

    # Construct the DataFrame
    df = pl.DataFrame(records)
    return df.lazy() if lazy else df
