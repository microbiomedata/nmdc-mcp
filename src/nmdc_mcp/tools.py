################################################################################
# nmdc_mcp/tools.py
# This module contains tools that consume the generic API wrapper functions in
# nmdc_mcp/api.py and constrain/transform them based on use cases/applications
################################################################################
from typing import Any, Dict, List, Optional
from datetime import datetime
from .api import fetch_nmdc_biosample_records_paged


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


def get_samples_by_ecosystem(
    ecosystem_type: Optional[str] = None,
    ecosystem_category: Optional[str] = None,
    ecosystem_subtype: Optional[str] = None,
    max_records: int = 50
) -> List[Dict[str, Any]]:
    """
    Fetch NMDC biosample records from a specific ecosystem type, category, or subtype.

    Args:
        ecosystem_type (str, optional): Type of ecosystem (e.g., "Soil", "Marine", "Host-associated")
        ecosystem_category (str, optional): Category of ecosystem (e.g., "Terrestrial", "Aquatic")
        ecosystem_subtype (str, optional): Subtype of ecosystem if available
        max_records (int): Maximum number of records to return

    Returns:
        List[Dict[str, Any]]: List of biosample records from the specified ecosystem
    """
    # Build filter criteria based on provided parameters
    filter_criteria = {}
    
    if ecosystem_type:
        filter_criteria["ecosystem_type"] = ecosystem_type
    
    if ecosystem_category:
        filter_criteria["ecosystem_category"] = ecosystem_category
        
    if ecosystem_subtype:
        filter_criteria["ecosystem_subtype"] = ecosystem_subtype
    
    # If no filters provided, return error message
    if not filter_criteria:
        return [{"error": "At least one ecosystem parameter (type, category, or subtype) must be provided"}]

    # Fields to retrieve
    projection = [
        "id", 
        "name", 
        "collection_date", 
        "ecosystem", 
        "ecosystem_category", 
        "ecosystem_type",
        "ecosystem_subtype",
        "env_broad_scale",
        "env_local_scale",
        "env_medium",
        "geo_loc_name"
    ]

    records = fetch_nmdc_biosample_records_paged(
        filter_criteria=filter_criteria,
        projection=projection,
        max_records=max_records,
        verbose=True
    )

    # Format the collection_date field to make it more readable
    for record in records:
        if "collection_date" in record and isinstance(record["collection_date"], dict):
            raw_date = record["collection_date"].get("has_raw_value", "")
            if raw_date:
                # Clean up the timestamp format
                try:
                    dt = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
                    record["collection_date"] = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
                except ValueError:
                    # Keep original if parsing fails
                    record["collection_date"] = raw_date

    return records
