################################################################################
# nmdc_mcp/main.py
# This module sets up the FastMCP CLI interface
################################################################################

from fastmcp import FastMCP
from nmdc_mcp.tools import (
    get_samples_in_elevation_range,
    get_samples_within_lat_lon_bounding_box,
    get_samples_by_ecosystem
)


# Create the FastMCP instance at module level
mcp = FastMCP("nmdc_mcp")

# Register all tools
mcp.tool(get_samples_in_elevation_range)
mcp.tool(get_samples_within_lat_lon_bounding_box)
mcp.tool(get_samples_by_ecosystem)


def main():
    """Main entry point for the application."""
    mcp.run()


if __name__ == "__main__":
    main()
