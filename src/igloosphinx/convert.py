import polars as pl
import sphobjinv


def inventory_to_polars_df(
    inv: sphobjinv.Inventory,
    lazy: bool = False,
) -> pl.DataFrame:
    """
    Convert a sphobjinv.Inventory instance into a Polars DataFrame
    with columns:
      - domain_role (e.g. 'py:class')
      - fullname     (e.g. 'polars.Catalog')
      - display_name (e.g. '-' if omitted)
      - project_name
      - project_version
      - uri
    """
    records = []
    for item in inv.objects:
        records.append(
            {
                "domain_role": f"{item.domain}:{item.role}",  # e.g. 'py:class'
                "fullname": item.name,  # e.g. 'polars.Catalog'
                "display_name": item.dispname,  # '-' if omitted
                "project_name": inv.project,  # From sphobjinv.Inventory
                "project_version": inv.version,  # From sphobjinv.Inventory
                "uri": item.uri,  # Link reference, e.g. https://docs...
            },
        )

    df = pl.DataFrame(records)
    return df.lazy() if lazy else df
