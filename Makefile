.PHONY: test-coverage clean install dev format lint all server build upload-test upload release deptry mypy test-mcp test-mcp-extended test-integration test-unit test-real-api test-version clean-claude-demo clean-bacterial-pfam clean-python-demos clean-curl-demos clean-data-object-demos run-all-demos

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
	uv run pytest --cov=nmdc_mcp --cov-report=html --cov-report=term --durations=0 tests/

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

# Demonstrate PFAM domain search with biologist-friendly prompt
local/claude-demo-pfam-search.txt:
	claude \
		--debug \
		--verbose \
		--mcp-config agent-configs/local-nmdc-mcp-for-claude.json \
		--dangerously-skip-permissions \
		--print "I need to find data about microbiome samples that contain both PF04183 and PF06276 protein domains. Search the NMDC database and get data for just 1 biosample that has both of these PFAM domains. Then show me all the metadata for all GFF data objects in their native JSON format exactly as returned from the search - don't make any additional API calls." 2>&1 | tee $@

# Demonstrate the new consolidated GFF PFAM filtering tool with biologist-friendly prompt
local/claude-demo-gff-pfam-analysis.txt:
	claude \
		--debug \
		--verbose \
		--mcp-config agent-configs/local-nmdc-mcp-for-claude.json \
		--dangerously-skip-permissions \
		--print "I have a specific functional annotation file (data object nmdc:dobj-11-wcxahg62) and I want to analyze it for specific protein domains. Can you download this GFF file and filter it to show me all the annotations that contain either the PF13243 domain (helix-turn-helix transcriptional regulator) or the PF02401 domain (LysR substrate binding domain)? I'm particularly interested in understanding what genes have these regulatory domains. Please show me the first few matching annotations with their genomic coordinates and any functional descriptions." 2>&1 | tee $@

# Demonstrate combined workflow: find biosamples with PFAM domains, then analyze their GFF files
local/claude-demo-combined-pfam-workflow.txt:
	claude \
		--debug \
		--verbose \
		--mcp-config agent-configs/local-nmdc-mcp-for-claude.json \
		--dangerously-skip-permissions \
		--print "I need to find microbiome samples that contain both PF04183 and PF06276 protein domains, then analyze the actual functional annotation data for those samples. First, search for biosamples with these domains and show me their data objects. Then, pick the most suitable functional annotation GFF file and download it to show me the specific gene annotations that contain these PFAM domains. I want to see the actual genomic evidence for these protein domains." 2>&1 | tee $@

# Search for biosamples with common bacterial PFAMs
# works: PFAM:PF00005 and PFAM:PF00072 (ABC transporter + response regulator)
local/bacterial-pfam-search-extended.json:
	curl -X POST "https://data.microbiomedata.org/api/biosample/search?limit=100" \
		-H "Content-Type: application/json" \
		-d '{ \
			"conditions": [ \
				{ \
					"op": "==", \
					"field": "id", \
					"value": "PFAM:PF04183", \
					"table": "pfam_function" \
				}, \
				{ \
					"op": "==", \
					"field": "id", \
					"value": "PFAM:PF06276", \
					"table": "pfam_function" \
				} \
			] \
		}' | jq '.' > $@

# Extract clean data: minimal activity info with rich output metadata
local/bacterial-pfam-clean.json: local/bacterial-pfam-search-extended.json
	jq '{ \
		biosample_count: .count, \
		samples: [ \
			.results[] | { \
				biosample_id: .id, \
				study_id: .study_id, \
				activities: [ \
					.omics_processing[].omics_data[] | { \
						activity_id: .id, \
						activity_type: .type, \
						analysis_category: (.metaproteomics_analysis_category // null), \
						informed_by: [ \
							.was_informed_by[]? | { \
								id: .id, \
								type: .annotations.type, \
								omics_type: .annotations.omics_type \
							} \
						], \
						outputs: [ \
							.outputs[]? | { \
								id: .id, \
								name: .name, \
								description: .description, \
								file_type: .file_type, \
								file_type_description: .file_type_description, \
								file_size_bytes: .file_size_bytes, \
								md5_checksum: .md5_checksum, \
								url: .url, \
								downloads: .downloads, \
								selected: .selected \
							} \
						] \
					} \
				] \
			} \
		] \
	}' $< > $@


# these all need individual refinement
#claude-demo-all: clean-claude-demo local/claude-demo-studies-with-publications.txt local/claude-demo-biosample-data-objects.txt

clean-claude-demo:
	rm -f local/claude-demo-*.txt

# Use the new comprehensive PFAM domain search tool
local/pfam-tool-test.json:
	python3 scripts/test_biosample_pfam_search.py 2>/dev/null > $@

# Test the new consolidated MCP tool for GFF filtering
local/mcp-gff-pfam-tool-test.json:
	@echo "🧪 Testing new MCP GFF PFAM filtering tool..."
	python3 scripts/test_gff_pfam_tool.py > $@

# Python-based data object workflow demonstration (legacy - will be replaced by mcp-gff-pfam-tool-test)
local/python-data-object-demo.json:
	@echo "🐍 Running Python GFF fetch and PFAM filtering demonstration..."
	python3 scripts/demo_fetch_gff_and_filter_pfam.py > $@

# Curl-based data object workflow demonstration (step-by-step)
# Step 1: Get data object metadata with download URL from runtime API
local/curl-data-object-metadata.json:
	@echo "🔍 Fetching data object metadata with download URL (curl)..."
	curl -H "Accept: application/json" \
		"https://api.microbiomedata.org/data_objects/nmdc%3Adobj-11-wcxahg62" \
		| jq '.' > $@

# Step 2: Download content from resolved URL (sample first 1MB for demonstration)
local/curl-data-object-content.gff: local/curl-data-object-metadata.json
	@echo "📥 Downloading content sample from resolved URL (curl)..."
	@URL=$$(jq -r '.url' $<); \
	echo "Downloading from: $$URL"; \
	curl "$$URL" --range 0-1048576 -o $@

# Step 3: Process downloaded content (filter for PFAM domains)
local/curl-pfam-filtered.gff: local/curl-data-object-content.gff
	@echo "🔬 Filtering content for PFAM domains PF13243 and PF02401 (curl)..."
	grep -E "pfam=.*PF13243|pfam=.*PF02401" $< > $@ || echo "No matching PFAM domains found in sample"

# Metatarget to run all demo targets (excluding Claude demos)
run-all-demos: clean-bacterial-pfam clean-data-object-demos local/bacterial-pfam-clean.json local/pfam-tool-test.json local/mcp-gff-pfam-tool-test.json local/python-data-object-demo.json local/curl-pfam-filtered.gff
	@echo "✅ All demo targets completed successfully!"

# Cleanup targets organized by functionality
clean-bacterial-pfam:
	rm -f local/bacterial-pfam-search-extended.json local/bacterial-pfam-clean.json

clean-python-demos:
	rm -f local/python-data-object-demo.json local/pfam-tool-test.json local/mcp-gff-pfam-tool-test.json

clean-curl-demos:
	rm -f local/curl-data-object-metadata.json local/curl-data-object-content.gff local/curl-pfam-filtered.gff

clean-data-object-demos: clean-python-demos clean-curl-demos

clean-all: clean clean-claude-demo clean-bacterial-pfam clean-data-object-demos