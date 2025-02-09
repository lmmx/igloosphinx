# igloosphinx

**Accessing Intersphinx inventories for Python packages using PyPI metadata to locate documentation sites.**

`igloosphinx` provides a command-line interface and library access to Intersphinx inventories, enabling users to easily find and retrieve documentation for Python packages. The tool works by:

- Performing a PyPI metadata lookup to identify the documentation site for a given package.
- Making educated guesses about the location of the `objects.inv` file.
- Allowing users to review version changes and access relevant documentation seamlessly.

## Features

- **PyPI Metadata Lookup**: Automatically fetches the documentation URL from PyPI.
- **Intersphinx Inventory Retrieval**: Accesses and retrieves the `objects.inv` file for easy linking to documentation.
- **Version Change Review**: Provides functionality to review changes between different versions of the documentation.

## Installation

```bash
pip install igloosphinx[polars]
```

On older CPUs run:

```python
pip install igloosphinx[polars-lts-cpu]
```

**NOTE** Temporarily requires dev-branch Sphinx, either use

```sh
pip install git+https://github.com/sphinx-doc/sphinx.git
```

or

```sh
uv add git+https://github.com/sphinx-doc/sphinx.git
```

## Usage

```python
from igloosphinx import Inventory

# Create an Intersphinx instance for a specific package
intersphinx = Inventory(package_name="example-package")

# Fetch the documentation inventory
inventory = intersphinx.fetch_inventory()

# Review version changes
changes = intersphinx.review_version_changes()
```

## Contributing

1. **Issues & Discussions**: Please open a GitHub issue for bugs, feature requests, or questions.
2. **Pull Requests**: PRs are welcome! Add tests under `tests/`, update the docs, and ensure you run `pytest` locally.

## License

This project is licensed under the MIT License.
