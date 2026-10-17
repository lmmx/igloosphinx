# 2026-10-17 Viability

Louis asked a review session with Claude whether igloosphinx is dead on arrival, or
whether there is something here. The question came with some background. Griffe works
on similar ground and is slow, and igloosphinx was meant to build on Sphinx's inventory
primitives instead, but looking under the hood was not satisfying. This entry records
the session's view of the code at dd94cc4: why the current approach does not deliver,
how an `objects.inv` client differs from griffe, a bug found in sphobjinv along the way,
and why a client is worth pursuing. It also records the avenues discussed, including
one Louis rejected and one he thinks sounds silly on first hearing. The structured
state is at the end.

All timings are single runs, taken on 2026-10-17 from a cloud container. The scratch
scripts used for them are not checked in. The `native` parser mentioned below is about
15 lines of Polars, described in the next section.

## What igloosphinx does at dd94cc4

`Inventory.fetch_inventory` chains three steps:

1. `pypi_docs_url.get_intersphinx_url(package)` fetches the PyPI JSON for the package.
   It takes a documentation URL candidate from it, then sends `HEAD` requests one after
   another to up to seven suffixes: `objects.inv`, `stable/`, `en/stable/`, `latest/`,
   `en/latest/`, `doc/`, `docs/`. It has a fallback that reads a `docs-python.yml`
   workflow from GitHub.
2. `sphobjinv.Inventory(url=...)` downloads the file, decompresses it, and builds one
   attrs `DataObjStr` per line.
3. `inventory_to_polars_df` loops over those objects in Python, builds a list of dicts,
   and calls `pl.DataFrame(records)`.

Every decision is delegated to one of two libraries, and the glue between them drops
the information that makes an inventory useful.

## Why the approach does not deliver

**sphobjinv is the wrong primitive for a columnar result.** An `objects.inv` file is a
four-line plaintext header followed by a zlib stream of lines:
`name domain:role priority uri dispname`. Sphinx parses those lines with one regex. A
DataFrame-shaped result wants that regex run over a whole column: decompress, split
lines into a `pl.Series`, run `str.extract_groups` with Sphinx's pattern, and resolve
`$` and `-` with `pl.when`. igloosphinx does something different. It builds about 20k
validated Python objects per inventory, then copies their fields into dicts, then into
columns. Measured on five real inventories, sphobjinv plus the conversion against the
`native` columnar parse:

| inventory          | rows   | sphobjinv parse | → DataFrame | native  |
|--------------------|-------:|----------------:|------------:|--------:|
| docs.python.org/3  | 20,176 | 0.129 s         | 0.086 s     | 0.053 s |
| pandas             | 15,968 | 0.180 s         | 0.065 s     | 0.070 s |
| scipy              | 11,924 | 0.086 s         | 0.033 s     | 0.037 s |
| numpy              |  8,274 | 0.068 s         | 0.024 s     | 0.018 s |
| polars             |  3,352 | 0.019 s         | 0.005 s     | 0.013 s |

The columnar parse is 2–6× faster and gives the same row counts on all five.

**The parse is not where the time goes, though.** End to end on 2026-10-17:

| package | `import igloosphinx` | discovery | fetch + parse | total  |
|---------|---------------------:|----------:|--------------:|-------:|
| polars  | 0.39 s               | 1.15 s    | 0.47 s        | ~2.0 s |
| pandas  | 0.26 s               | 0.34 s    | 0.82 s        | ~1.4 s |
| numpy   | 0.24 s               | 0.37 s    | 0.57 s        | ~1.2 s |

The PRD's 500 ms target cannot be met through faster parsing. Discovery does sequential
`HEAD` probes and is repeated on every call, because nothing is cached. The
Polars import alone uses most of the 500 ms budget. A fast client has to stop
rediscovering URLs it has already found, and has to fetch several inventories at once.

**The output is not a usable link table.** `convert.py` copies `item.uri` and
`item.dispname` raw. Sphinx abbreviates a URI ending in `$` (the `$` stands for the
name) and a display name of `-` (meaning "same as the name"). In scipy's inventory,
6,553 of 11,924 URIs end in `$` and 6,502 display names are `-`, so most rows hold the
abbreviation instead of the value. The documentation base URL is also thrown away once
the file has been fetched, so every `uri` is relative and has nothing to be relative to.
`project_version` holds Sphinx's `version` string (for example `21.4`), which is not
necessarily the URL slug the file came from (`/en/21.4.0/`).

**The error paths contradict the PRD.** When discovery finds nothing,
`get_intersphinx_url` returns `None`. `sphobjinv.Inventory(url=None)` then counts zero
sources and builds an empty "manual" inventory, and the CLI prints a 0×0 frame and exits
0. A library function that raises `SystemExit` on a discovery exception also falls
outside the CLI's `except Exception` handler.

**Several pieces are placeholders.**
- `version=` is stored and never used.
- `lazy=True` turns the frame into a LazyFrame and immediately collects it again.
- `review_version_changes` returns a one-row frame of its own arguments.
- The single test patches out discovery, sphobjinv and the converter, and checks the
  column names of its own mock.

**Polars packaging.** igloosphinx declares `polars>=1.30.0` as a hard dependency and has
an `lts-cpu` extra. The README tells users to install `[polars]` or `[polars-lts-cpu]`.
Louis has since moved polars-genson to optional `polars` and `rtcompat` extras pinned to
`polars>=2.0.0` (polars-genson-py/pyproject.toml), because `polars-lts-cpu` is deprecated
in favour of `polars[rtcompat]`. igloosphinx's code runs unchanged on Polars 2.0.0:
`inventory_to_polars_df` and `fetch_inventory("polars")` both work in a scratch
environment. Only the packaging metadata still describes the old arrangement.

## How this differs from griffe

Griffe and an inventory client answer different questions, and the speed difference
follows from that.

|                       | griffe                                                   | `objects.inv` client |
|-----------------------|----------------------------------------------------------|----------------------|
| describes             | what the **code** exposes: signatures, docstrings, aliases, parsed by visiting the AST, with optional runtime inspection | what the **documentation** publishes: name, role, anchor URL |
| needs                 | the package source on disk                               | one HTTP GET of 36–205 KB (the five files above) |
| cost                  | static load without alias resolution: polars 0.67 s / 9,757 members, numpy 2.18 s / 18,681, pandas 6.10 s / 52,250 | 0.2–0.5 s fetch, 0.02–0.07 s columnar parse |
| older versions        | the older source                                         | any build the docs host still serves, e.g. `www.attrs.org/en/21.4.0/objects.inv` |
| who writes the format | griffe itself                                            | Sphinx, plus the other doc generators that emit Sphinx inventories (mkdocstrings, pydoctor) |

Griffe is slow because it does more: it resolves the real API surface from code.
An inventory is precomputed at docs build time, so reading one costs a download and a
regex. This is not a cheaper griffe, and it is not a port. The two overlap only at "list
the public names of a package", and even there they answer differently. Griffe gives the
names the code defines. The inventory gives the names the authors chose to document,
under the paths they chose to document them at.

## The sphobjinv bug

`sphobjinv.Inventory(source)` guesses the format of a bytes argument by trying importers
in a fixed order, with the plaintext importer first. Each importer swallows only the
exceptions listed for it, and for plaintext bytes that list is just `TypeError`
(sphobjinv 2.4, inventory.py `_general_import`). The plaintext importer runs the
data-line regex `pb_data` over the raw bytes. On a compressed file this should match
nothing, which raises `TypeError("No objects found")` and moves on to the zlib importer.

But zlib output is effectively random bytes, and `pb_data` is permissive (roughly:
non-space, space, `x:y`, space, integer, space, non-space, space, rest of line). Every
so often a compressed stream contains a stretch that matches. sphobjinv then tries to
decode that stretch as UTF-8, `DataObjStr` raises `UnicodeDecodeError`, the exception
is not on the swallow list, and the import fails. Of the five inventories downloaded
on 2026-10-17, scipy's has exactly one such match. The other four have zero.

igloosphinx at dd94cc4 does **not** hit this. `Inventory(url=...)` goes straight to
`_import_zlib_bytes`, and `Inventory(zlib=raw)` and `Inventory(fname_zlib=path)` avoid
it too. But any client that fetches bytes itself (for caching, for concurrent fetches,
or to keep the base URL) and passes them as a plain `source` has a failure rate that
depends on the data. The format declares itself on its fourth line ("The remainder of
this file is compressed using zlib"), so sniffing the content was never necessary. This
is one more reason not to sit on top of sphobjinv. The header tells a parser what it is
reading.

## Why a client is worth pursuing

The thing worth having is a fast client. Given a package name (and optionally a version
or a known URL), it returns a fully resolved table: absolute URL, expanded display name,
domain and role split into columns, priority, the project and version from the header,
and the URL slug it came from. It does this in one request once the URL is known. That
covers several jobs griffe cannot do cheaply:
- resolving a qualified name to its exact docs anchor without installing anything;
- listing what a package documents;
- comparing two hosted builds of the docs.

**Rejected: a corpus instead of a client.** The session first suggested that the
lasting value lies in a corpus: snapshots of inventories for the top N PyPI packages
across versions, stored as Parquet, with the client as a detail. Louis rejected this as
misguided. igloosphinx is a client. Building snapshots in advance for a chosen subset
of packages is fine, as a warm cache or as test fixtures, but it is not the product.

## Avenues

### Columnar parser, header-driven

Replace sphobjinv with a parser that reads the header, checks the "compressed using
zlib" line, decompresses, and runs Sphinx's line regex as one `str.extract_groups`. Then
resolve `$` and `-`, join the base URL, and split `domain:role`. Measured above at
2–6× faster than sphobjinv plus conversion, and immune to the sniffing bug by
construction.

### Discovery that is not repeated

The 0.34–1.15 s discovery step is the largest cost that is not network fetch. Options:
- cache resolved `objects.inv` URLs per package;
- run the `HEAD` probes concurrently, not one after another;
- accept an explicit URL;
- read known mappings from intersphinx-registry's `registry.json`
  (https://pypi.org/project/intersphinx-registry), which maps package names to
  intersphinx URLs and notes that it downloads every inventory on every run, with no
  cache.

### Version-aware fetching and diffing

Read the Docs and similar hosts serve one inventory per kept build, under a version
slug. attrs serves `21.4.0`, `22.2.0`, `23.1.0` and `stable`, and all four returned 200
on 2026-10-17. Diffing two builds is what `review_version_changes` was meant to do. A
raw anti-join on `(name, domain_role)` between attrs 21.4 and stable (26.1) gives 60
added and 13 removed `py:` entries, but the removals are mostly noise:
- 12 of the 13 removed names match a stable name once a doubled first segment is
  dropped. `attr.attr.evolve` in 21.4 is `attr.evolve` in stable. The 21.4 docs used a
  `currentmodule` that prefixed the module twice, which is a documentation artefact,
  not an API change.
- The one remaining removal is `attrs.validators.provides`.
- URI anchors give no extra matching signal. Sphinx's Python domain uses the qualified
  name as the anchor (`api.html#attr.attr.evolve`, `api-attr.html#attr.evolve`), so
  anchors change exactly when names do. This contradicts the session's earlier guess
  that anchors would be the more stable key.

The craft of this avenue is therefore in canonicalising names (collapsing doubled
prefixes, re-export paths) and in telling "page moved" (`api.html` → `api-attr.html`)
apart from "symbol renamed". Version slugs also differ between projects (`21.4.0`
against the header's `21.4`), so probing for slugs is part of the job.

### Resolver for agents

Given `polars.DataFrame.join`, return the exact anchor URL, then fetch only that
section of the page. Scraping-based doc tools tend to land on the wrong page. A
web search on 2026-10-17 found no MCP server built on `objects.inv`, which is not proof
that none exists. This uses the client as-is plus a section extractor.

### Docs drift against griffe — Louis: sounds silly off the bat

Join griffe's public API for a package against its inventory, and report public
symbols with no docs entry and documented symbols that no longer exist in code.

Louis's first reaction is that this sounds like a silly idea, and the reasons are
visible already:
- Inventory coverage is an editorial choice. autosummary lists and `currentmodule`
  directives decide what gets documented, so "undocumented" mostly means
  "intentionally not listed".
- Griffe reports canonical definition paths (`attr._make.Converter`), while docs use
  public re-export paths (`attrs.Converter`). The join would mostly measure path
  mismatch, which then has to be resolved through griffe's alias graph before anything
  is left to report.
- The attrs diff above shows the docs side alone already carries prefix artefacts
  that have nothing to do with the code.

Recorded here as written up, not as planned work.

## Current State

- `Inventory.fetch_inventory` calls `_discover_objects_inv` then `_parse_inventory`
  (src/igloosphinx/inventory.py:37-46)
- `_discover_objects_inv` calls `pypi_docs_url.get_intersphinx_url`, which fetches the
  PyPI JSON then sends sequential `HEAD` requests to up to 7 `objects.inv` suffixes per
  candidate URL (src/igloosphinx/inventory.py:60-70, pypi_docs_url/docs_intersphinx.py)
- `_discover_objects_inv` prints the exception and raises `SystemExit(1)` when
  `get_intersphinx_url` raises (src/igloosphinx/inventory.py:65-69)
- `_parse_inventory` passes the URL to `sphobjinv.Inventory(url=...)`, which imports the
  download through `_import_zlib_bytes` without format sniffing
  (src/igloosphinx/inventory.py:76-80)
- `inventory_to_polars_df` builds one dict per sphobjinv object in a Python loop and
  calls `pl.DataFrame(records)` (src/igloosphinx/convert.py:19-33)
- `inventory_to_polars_df` copies `item.uri` and `item.dispname` unexpanded — in the
  scipy inventory 6,553 of 11,924 `uri` values end in `$` and 6,502 of 11,924
  `display_name` values are `-` (src/igloosphinx/convert.py:25, 28)
- The DataFrame from `fetch_inventory` holds `uri` relative to the docs root, and no
  column or attribute keeps the docs base URL (src/igloosphinx/convert.py:23-28,
  src/igloosphinx/inventory.py:43-45)
- `get_intersphinx_url("igloosphinx")` returns `None`, and `fetch_inventory` then
  returns a 0×0 DataFrame — `sphobjinv.Inventory(url=None)` counts zero sources and
  builds an empty manual inventory; `igloosphinx igloosphinx` prints the empty frame and
  exits 0
- `lazy=True` turns the converted frame into a LazyFrame and collects it, so
  `fetch_inventory` returns a `pl.DataFrame` for both values of `lazy`
  (src/igloosphinx/convert.py:33, src/igloosphinx/inventory.py:82-84)
- The CLI writes CSV for `--format csv`, JSON for `--format json`, and the frame's repr
  for any other value (src/igloosphinx/cli.py:32-40)
- `tests/inventory_test.py` patches `_discover_objects_inv`, `sphobjinv.Inventory` and
  `inventory_to_polars_df`, and asserts the column names of its own mock frame
  (tests/inventory_test.py:14-41)
- uv.lock resolves polars 1.39.3 and sphobjinv 2.4; `inventory_to_polars_df` and
  `fetch_inventory("polars")` run on polars 2.0.0 in a scratch environment
- Timings on 2026-10-17, single run: `import igloosphinx` 0.24-0.39 s, discovery
  0.34-1.15 s, fetch and parse 0.47-0.82 s for polars, pandas and numpy
- sphobjinv 2.4 `Inventory(source=<bytes>)` tries the plaintext importer first and
  swallows only `TypeError` from it — the scipy inventory's zlib stream holds one
  `pb_data` regex match, so `Inventory(source=raw)` on that file raises
  `UnicodeDecodeError`, while `Inventory(url=...)` and `Inventory(fname_zlib=...)`
  import 11,924 objects (sphobjinv/inventory.py `_general_import`, `_try_import`)
- docs/JOURNAL.md holds a byte-identical copy of lmmx/giacometti docs/JOURNAL.md at
  2ca57fe

## Stubbed

- `review_version_changes` returns a one-row DataFrame of its `from_v` and `to_v`
  arguments (src/igloosphinx/inventory.py:48-58)
- `Inventory.__init__` stores `version` and no method reads `self.version`
  (src/igloosphinx/inventory.py:21, 33)

## Missing

- No parser in igloosphinx reads the `objects.inv` header or decompresses the zlib
  stream — parsing goes through sphobjinv (src/igloosphinx/inventory.py:77)
- No caching of discovered URLs or downloaded inventories
- No fetching of an inventory by version slug, and no comparison of two inventories
- No option to pass an `objects.inv` URL directly — `fetch_inventory` always runs
  discovery (src/igloosphinx/inventory.py:43)
- No test makes a network request or parses a real inventory (tests/inventory_test.py)

## Divergence

- README states "Version Change Review: Provides functionality to review changes
  between different versions of the documentation" (README.md:22), and
  `review_version_changes` returns its arguments (src/igloosphinx/inventory.py:58)
- README installs `igloosphinx[polars]` and `igloosphinx[polars-lts-cpu]`
  (README.md:27, 33), and pyproject.toml declares polars as a hard dependency and one
  extra named `lts-cpu` (pyproject.toml:24, 46)
- pyproject.toml lists Python 3.9 and 3.10 classifiers (pyproject.toml:38-39) with
  `requires-python = ">=3.11"` (pyproject.toml:21)
- PRD.md requires meaningful errors for missing inventories and CLI exit codes
  (PRD.md:24-25), and a package with no discoverable inventory gives an empty frame
  with exit 0
- PRD.md targets retrieval and parsing under 500 ms (PRD.md:44, 64), and the measured
  totals for polars, pandas and numpy are 1.2-2.0 s
- PRD.md lists caching as a secondary feature (PRD.md:28), and no cache exists in
  src/igloosphinx
