################################################################################
# nmdc_mcp/main.py
# This module sets up the FastMCP CLI interface
################################################################################

from fastmcp import FastMCP

from nmdc_mcp.tools import (
    get_all_collection_ids,
    get_biosamples_for_study,
    get_collection_names,
    get_collection_stats,
    get_entities_by_ids_with_projection,
    get_entity_by_id,
    get_entity_by_id_with_projection,
    get_random_collection_ids,
    get_samples_by_ecosystem,
    get_samples_in_elevation_range,
    get_samples_within_lat_lon_bounding_box,
    get_study_doi_details,
    get_study_for_biosample,
    search_studies_by_doi_criteria,
)

# Create the FastMCP instance at module level
mcp: FastMCP = FastMCP("nmdc_mcp")

# Register all tools
mcp.tool(get_collection_names)
mcp.tool(get_collection_stats)
mcp.tool(get_all_collection_ids)
mcp.tool(get_random_collection_ids)
mcp.tool(get_samples_in_elevation_range)
mcp.tool(get_samples_within_lat_lon_bounding_box)
mcp.tool(get_samples_by_ecosystem)
mcp.tool(get_entity_by_id)
mcp.tool(get_entity_by_id_with_projection)
mcp.tool(get_entities_by_ids_with_projection)
mcp.tool(get_study_for_biosample)
mcp.tool(get_biosamples_for_study)
mcp.tool(get_study_doi_details)
mcp.tool(search_studies_by_doi_criteria)


def main() -> None:
    """Main entry point for the application."""
    mcp.run()


if __name__ == "__main__":
    main()
