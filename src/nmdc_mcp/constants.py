"""
Constants used across the NMDC MCP package.
"""

BASE_URL = "https://api-backup.microbiomedata.org"
"""Production Runtime API base URL"""

# API Configuration
DEFAULT_PAGE_SIZE = 100
"""Default number of records to fetch per API page."""

MAX_ENTITY_IDS_PER_REQUEST = 100
"""Maximum number of entity IDs that can be requested in a single batch operation."""

# Other API limits
MAX_RANDOM_SAMPLE_SIZE = 1000
"""Maximum number of random IDs that can be requested."""

DEFAULT_RANDOM_SAMPLE_SIZE = 1000
"""Default number of random IDs to return."""

LARGE_COLLECTION_THRESHOLD = 10000
"""Threshold for determining if a collection is considered large."""

# Fetch multipliers for random sampling
RANDOM_FETCH_MULTIPLIER = 10
"""Multiplier for fetching extra records to enable random sampling."""

MIN_RANDOM_FETCH_COUNT = 100
"""Minimum number of records to fetch for random sampling."""
