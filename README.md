# NMDC MCP

A fastmcp-based tool for writing prompts against data in the NMDC database.

## Installation

You can install the package from source:

```bash
pip install -e .
```

Or using uv:

```bash
uv pip install -e .
```

## Usage

You can use the CLI:

```bash
nmdc-mcp
```

Or import in your Python code:

```python
from nmdc_mcp.main import create_mcp

mcp = create_mcp()
mcp.run()
```

## Development

### Local Setup

```bash
# Clone the repository
git clone https://github.com/username/nmdc-mcp.git
cd nmdc-mcp

# Install development dependencies
uv pip install -e ".[dev]"
```

### Running Tests

```bash
pytest
```

## License

MIT