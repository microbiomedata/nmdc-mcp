# NMDC MCP

A fastmcp-based tool for writing prompts against data in the NMDC database.

## Installation

You can install the package from source using uv:

```bash
uv sync
```

## Usage

You can use the CLI:

```bash
nmdc-mcp
```

Or import in your Python code: # TODO incorrect instructions

```python
from nmdc_mcp.main import create_mcp

mcp = create_mcp()
mcp.run()
```

Or utilize the nmdc_mcp.client by running 

```bash
uv run 'path/to/nmdc_mcp/client.py' 'path/to/nmdc_mcp/main.py'
```

Or using python

```bash
python 'path/to/nmdc_mcp/client.py' 'path/to/nmdc_mcp/main.py'
```


## Development

### Local Setup

```bash
# Clone the repository
git clone https://github.com/microbiomedata/nmdc-mcp.git
cd nmdc-mcp

# Install development dependencies
make dev
```

### Development Workflow

The project uses a comprehensive Makefile for development tasks:

```bash
# Run all development checks (tests, formatting, linting, type checking)
make all

# Individual commands
make dev           # Install development dependencies
make test-coverage # Run tests with coverage
make format        # Format code with black
make lint          # Lint with ruff
make mypy          # Type checking
make deptry        # Check for unused dependencies
make build         # Build package
```

### Testing

```bash
# Run all tests with coverage
make test-coverage

# Run specific test types
make test-unit         # Unit tests only
make test-integration  # Integration tests
make test-real-api     # Tests against real NMDC API
make test-mcp          # Test MCP protocol
```

### MCP Integration

#### Claude Desktop Setup
Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "nmdc-mcp": {
      "command": "uvx",
      "args": ["nmdc-mcp"]
    }
  }
}
```

#### Claude Code MCP Setup
```bash
claude mcp add -s project nmdc-mcp uvx nmdc-mcp
```

#### Goose Setup
```bash
goose session --with-extension "uvx nmdc-mcp"
```

## License

MIT