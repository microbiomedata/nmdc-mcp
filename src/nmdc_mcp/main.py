################################################################################
# nmdc_mcp/main.py
# This module sets up the FastMCP CLI interface
################################################################################
import sys
from importlib import metadata

from fastmcp import FastMCP

from nmdc_mcp.tools import (
    fetch_and_filter_gff_by_pfam_domains,
    get_all_collection_ids,
    get_biosamples_for_study,
    get_collection_names,
    get_collection_stats,
    get_data_objects_by_pfam_domains,
    get_entities_by_ids_with_projection,
    get_entity_by_id,
    get_entity_by_id_with_projection,
    # get_random_collection_ids,  # Disabled - removes random sampling
    # get_samples_by_annotation,  # Disabled - replaced by get_data_objects_by_pfam_domains  # noqa
    get_samples_by_ecosystem,
    get_samples_in_elevation_range,
    get_samples_within_lat_lon_bounding_box,
    get_study_doi_details,
    get_study_for_biosample,
    search_studies_by_doi_criteria,
)

try:
    __version__ = metadata.version("nmdc-mcp")
except metadata.PackageNotFoundError:
    __version__ = "unknown"

# Create the FastMCP instance at module level
mcp: FastMCP = FastMCP(
    "nmdc_mcp",
    description=(
        "NMDC (National Microbiome Data Collaborative) API tools for accessing "
        "microbiome data, biosamples, studies, and functional annotations. "
        "Provides access to genomic data objects, PFAM domain analysis, and "
        "ecosystem-based sample searches."
    ),
)

# Register all tools
mcp.tool(
    fetch_and_filter_gff_by_pfam_domains,
    description=(
        "Use this tool when users want to analyze a specific GFF annotation file "
        "for PFAM protein domains. Given a data object ID and list of PFAM "
        "domains, this tool downloads the GFF file content and filters for "
        "annotations containing those domains. Perfect for analyzing functional "
        "annotations in genomic data."
    ),
)
mcp.tool(
    get_data_objects_by_pfam_domains,
    description=(
        "Use this tool to find biosamples that contain specific PFAM protein "
        "domains. Returns structured data about biosamples, their activities, "
        "and data objects. Perfect for finding samples with particular "
        "functional capabilities."
    ),
)
mcp.tool(
    get_collection_names,
    description=(
        "Use this tool to discover what types of data are available in the "
        "NMDC database. Returns a list of collection names like "
        "'biosample_set', 'study_set', etc."
    ),
)
mcp.tool(
    get_collection_stats,
    description=(
        "Use this tool to get statistics about NMDC collections including "
        "document counts. Helps understand the size and scope of available data."
    ),
)
mcp.tool(
    get_all_collection_ids,
    description=(
        "Use this tool to get lists of IDs from NMDC collections in batches. "
        "Useful for sampling or systematic analysis of large datasets."
    ),
)
# mcp.tool(get_random_collection_ids)  # Disabled - removes random sampling
mcp.tool(
    get_samples_in_elevation_range,
    description=(
        "Use this tool to find biosamples collected within a specific "
        "elevation range. Perfect for studying altitude-related microbial "
        "communities."
    ),
)
mcp.tool(
    get_samples_within_lat_lon_bounding_box,
    description=(
        "Use this tool to find biosamples collected within a specific "
        "geographic bounding box defined by latitude and longitude coordinates."
    ),
)
mcp.tool(
    get_samples_by_ecosystem,
    description=(
        "Use this tool to find biosamples from specific ecosystem types, "
        "categories, or subtypes. Perfect for studying particular environments "
        "like soil, marine, or host-associated microbiomes."
    ),
)
# mcp.tool(get_samples_by_annotation)  # Disabled - replaced by find_data_objects_by_pfam_domains  # noqa
mcp.tool(
    get_entity_by_id,
    description=(
        "Use this tool to retrieve any NMDC entity by its ID. Works with "
        "biosamples, studies, data objects, and other NMDC entities."
    ),
)
mcp.tool(
    get_entity_by_id_with_projection,
    description=(
        "Use this tool to retrieve specific fields from an NMDC entity by ID. "
        "More efficient than getting full entities when you only need certain "
        "fields."
    ),
)
mcp.tool(
    get_entities_by_ids_with_projection,
    description=(
        "Use this tool to retrieve specific fields from multiple NMDC entities "
        "by their IDs. Efficient for batch operations with field filtering."
    ),
)
mcp.tool(
    get_study_for_biosample,
    description=(
        "Use this tool to find the study associated with a specific biosample. "
        "Returns study information and metadata."
    ),
)
mcp.tool(
    get_biosamples_for_study,
    description=(
        "Use this tool to find all biosamples associated with a specific study. "
        "Returns a list of biosample IDs and metadata."
    ),
)
mcp.tool(
    get_study_doi_details,
    description=(
        "Use this tool to get detailed DOI information for a study, including "
        "publication DOIs, dataset DOIs, and award DOIs."
    ),
)
mcp.tool(
    search_studies_by_doi_criteria,
    description=(
        "Use this tool to search for studies based on DOI criteria like "
        "provider, category, or DOI value patterns. Perfect for finding "
        "published studies or datasets from specific sources."
    ),
)


def main() -> None:
    """Main entry point for the application."""
    if "--version" in sys.argv:
        print(__version__)
        sys.exit(0)
    mcp.run()


if __name__ == "__main__":
    main()
