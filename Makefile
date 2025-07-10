.PHONY: test-coverage clean install dev format lint all server build upload-test upload release deptry mypy test-mcp test-mcp-extended test-integration test-unit test-real-api

# Default target
all: clean install dev test-coverage format lint mypy deptry build test-mcp test-mcp-extended test-integration

# Install everything for development
dev:
	uv sync --group dev

# Install production only
install:
	uv sync

# Run tests with coverage
test-coverage:
	uv run pytest --cov=nmdc_mcp --cov-report=html --cov-report=term tests/

# Clean up build artifacts
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf htmlcov/
	rm -f .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf src/*.egg-info

# Run server mode
server:
	uv run python src/nmdc_mcp/main.py

# Format code with black
format:
	uv run black src/ tests/

lint:
	uv run ruff check --fix src/ tests/

# Check for unused dependencies
deptry:
	uvx deptry .

# Type checking
mypy:
	uv run mypy src/

# Build package with uv
build:
	uv build

# Upload to TestPyPI (using token-based auth)
upload-test:
	uv run twine upload --repository testpypi dist/*

# Upload to PyPI (using token-based auth - set TWINE_PASSWORD environment variable first)
upload:
	uv run twine upload dist/*

# Complete release workflow (mirrors original CI approach)
release: clean install test-coverage build

# Integration Testing
test-integration:
	@echo "🔬 Testing NMDC integration..."
	uv run pytest tests/test_integration.py -v -m integration

# Run all unit tests (mocked)
test-unit:
	@echo "🧪 Running unit tests..."
	uv run pytest tests/test_api.py tests/test_tools.py -v

# Run integration tests that hit real API
test-real-api:
	@echo "🌐 Testing against real NMDC API..."
	uv run pytest tests/test_integration.py -v -m integration

# MCP Server testing
test-mcp:
	@echo "Testing MCP protocol with tools listing..."
	@(echo '{"jsonrpc": "2.0", "method": "initialize", "params": {"protocolVersion": "2025-03-26", "capabilities": {"tools": {}}, "clientInfo": {"name": "test-client", "version": "1.0.0"}}, "id": 1}'; \
	 sleep 0.1; \
	 echo '{"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}'; \
	 sleep 0.1; \
	 echo '{"jsonrpc": "2.0", "method": "tools/list", "id": 2}') | \
	uv run python src/nmdc_mcp/main.py

test-mcp-extended:
	@echo "Testing MCP protocol with tool execution..."
	@(echo '{"jsonrpc": "2.0", "method": "initialize", "params": {"protocolVersion": "2025-03-26", "capabilities": {"tools": {}}, "clientInfo": {"name": "test-client", "version": "1.0.0"}}, "id": 1}'; \
	 sleep 0.1; \
	 echo '{"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}'; \
	 sleep 0.1; \
	 echo '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "get_samples_by_ecosystem", "arguments": {"ecosystem_type": "Soil", "max_records": 3}}, "id": 2}') | \
	uv run python src/nmdc_mcp/main.py

# NMDC MCP - Claude Desktop config:
#   Add to ~/Library/Application Support/Claude/claude_desktop_config.json:
#   {
#     "mcpServers": {
#       "nmdc-mcp": {
#         "command": "uvx",
#         "args": ["nmdc-mcp"]
#       }
#     }
#   }
#
# Claude Code MCP setup:
#   claude mcp add -s project nmdc-mcp uvx nmdc-mcp
#
# Goose setup:
#   goose session --with-extension "uvx nmdc-mcp"