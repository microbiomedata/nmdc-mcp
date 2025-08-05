.PHONY: test-coverage clean install dev format lint all server build upload-test upload release deptry mypy test-mcp test-mcp-extended test-integration test-unit test-real-api test-version clean-claude-demo claude-demo-all claude-demo-functional-annotation claude-demo-biosample-data-objects

# Default target
all: clean install dev test-coverage format lint mypy deptry build test-mcp test-mcp-extended test-integration test-version

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

# Upload to TestPyPI (using token-based auth - set UV_PUBLISH_TOKEN environment variable first)
upload-test:
	uv publish --publish-url https://test.pypi.org/legacy/

# Upload to PyPI (using token-based auth - set UV_PUBLISH_TOKEN environment variable first)  
upload:
	uv publish

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

# Test version flag
test-version:
	@echo "🔢 Testing version flag..."
	uv run nmdc-mcp --version

# --dangerously-skip-permissions is useful here for automation
# but is discouraged in production
local/claude-demo-studies-with-publications.txt:
	claude \
		--debug \
		--verbose \
		--mcp-config agent-configs/local-nmdc-mcp-for-claude.json \
		--dangerously-skip-permissions \
		--print "I need to find studies that have been published in journals. Can you help me get a list of published studies with their names?" 2>&1 | tee $@

# don't complete in claude cli in a reasonable amount of time
# goose seems to be able to handle the large response (and the need for saving to fiels)
local/claude-demo-functional-annotation.txt:
	claude \
		--debug \
		--verbose \
		--mcp-config agent-configs/local-nmdc-mcp-for-claude.json \
		--dangerously-skip-permissions \
		--print "I'm studying alcohol metabolism and need to find soil samples that contain genes for alcohol dehydrogenase (KEGG orthology K00001). Can you find me a few samples and tell me what ecosystems they're from?" 2>&1 | tee $@

# Demonstrate the new biosample/data object bridge functionality
local/claude-demo-biosample-data-objects.txt:
	claude \
		--debug \
		--verbose \
		--mcp-config agent-configs/local-nmdc-mcp-for-claude.json \
		--dangerously-skip-permissions \
		--print "I found a sample that has alcohol dehydrogenase genes, but now I need to download the actual genomic data files for my analysis. Can you help me find what data files are available for sample nmdc:bsm-11-002vgm56?" 2>&1 | tee $@

.PHONY: clean-claude-demo claude-demo-all

# these all need individual refinement
#claude-demo-all: clean-claude-demo local/claude-demo-studies-with-publications.txt local/claude-demo-biosample-data-objects.txt

clean-claude-demo:
	rm -f local/claude-demo-*.txt

