################################################################################
# nmdc_mcp/main.py
# This module sets up the FastMCP CLI interface
################################################################################

from fastmcp import FastMCP

from nmdc_mcp.tools import (
    get_entity_by_id,
    get_random_biosample_subset,
    get_random_collection_subset,
    get_samples_by_ecosystem,
    get_samples_in_elevation_range,
    get_samples_within_lat_lon_bounding_box,
)

# Create the FastMCP instance at module level
mcp: FastMCP = FastMCP("nmdc_mcp")

# Register all tools
mcp.tool(get_samples_in_elevation_range)
mcp.tool(get_samples_within_lat_lon_bounding_box)
mcp.tool(get_samples_by_ecosystem)
mcp.tool(get_entity_by_id)
mcp.tool(get_random_biosample_subset)
mcp.tool(get_random_collection_subset)


def main() -> None:
    """Main entry point for the application."""
    mcp.run()


if __name__ == "__main__":
    main()
