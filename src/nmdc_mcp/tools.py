################################################################################
# nmdc_mcp/tools.py
# This module contains tools that consume the generic API wrapper functions in
# nmdc_mcp/api.py and constrain/transform them based on use cases/applications
################################################################################
from typing import Any, Dict, List, Optional
from .api import fetch_nmdc_biosample_records_paged, fetch_taxa_abundance_data


def get_samples_in_elevation_range(
    min_elevation: int, max_elevation
) -> List[Dict[str, Any]]:
    """
    Fetch NMDC biosample records with elevation within a specified range.

    Args:
        min_elevation (int): Minimum elevation (exclusive) for filtering records.
        max_elevation (int): Maximum elevation (exclusive) for filtering records.

    Returns:
        List[Dict[str, Any]]: List of biosample records that have elevation greater 
            than min_elevation and less than max_elevation.
    """
    filter_criteria = {"elev": {"$gt": min_elevation, "$lt": max_elevation}}

    records = fetch_nmdc_biosample_records_paged(
        filter_criteria=filter_criteria,
        max_records=10,
    )

    return records


def get_samples_within_lat_lon_bounding_box(
    lower_lat: int, upper_lat: int, lower_lon: int, upper_lon: int
) -> List[Dict[str, Any]]:
    """
    Fetch NMDC biosample records within a specified latitude and longitude bounding box.

    Args:
        lower_lat (int): Lower latitude bound (exclusive).
        upper_lat (int): Upper latitude bound (exclusive).
        lower_lon (int): Lower longitude bound (exclusive).
        upper_lon (int): Upper longitude bound (exclusive).

    Returns:
        List[Dict[str, Any]]: List of biosample records that fall within the specified 
            latitude and longitude bounding box.
    """
    filter_criteria = {
        "lat_lon.latitude": {"$gt": lower_lat, "$lt": upper_lat},
        "lat_lon.longitude": {"$gt": lower_lon, "$lt": upper_lon},
    }

    records = fetch_nmdc_biosample_records_paged(
        filter_criteria=filter_criteria,
        max_records=10,
    )

    return records


def get_sample_taxonomic_profile(
    sample_id: str,
    rank: Optional[str] = None,
    min_abundance: float = 0.001,
    max_records: int = 50
) -> List[Dict[str, Any]]:
    """
    Get the taxonomic profile for a specific biosample.
    
    Args:
        sample_id: The ID of the biosample to analyze
        rank: Optional taxonomic rank to filter by (e.g., 'phylum', 'genus')
        min_abundance: Minimum relative abundance threshold (default: 0.001 or 0.1%)
        max_records: Maximum number of records to return
        
    Returns:
        List of taxonomic records for the specified sample, optionally filtered by rank
    """
    records = fetch_taxa_abundance_data(
        sample_id=sample_id,
        taxonomy_level=rank,
        min_abundance=min_abundance,
        max_records=max_records,
        verbose=True
    )
    
    return records
