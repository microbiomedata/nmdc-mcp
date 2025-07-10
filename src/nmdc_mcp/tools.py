################################################################################
# nmdc_mcp/tools.py
# This module contains tools that consume the generic API wrapper functions in
# nmdc_mcp/api.py and constrain/transform them based on use cases/applications
################################################################################
import random
from datetime import datetime
from typing import Any

from .api import (
    fetch_nmdc_biosample_records_paged,
    fetch_nmdc_collection_records_paged,
    fetch_nmdc_entity_by_id,
)

# Maximum random offset to apply when sampling to reduce ordering bias
# This limit prevents excessive API calls while still providing good randomization
MAX_RANDOM_OFFSET = 10000


def clean_collection_date(record: dict[str, Any]) -> None:
    """
    Clean up collection_date format in a record to be human-readable.
    Args:
        record: Dictionary containing a record that may have collection_date field
    """
    if "collection_date" in record and isinstance(record["collection_date"], dict):
        raw_date = record["collection_date"].get("has_raw_value", "")
        if raw_date:
            try:
                dt = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
                record["collection_date"] = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
            except ValueError:
                record["collection_date"] = raw_date


def get_samples_in_elevation_range(
    min_elevation: int, max_elevation: int
) -> list[dict[str, Any]]:
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
) -> list[dict[str, Any]]:
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
    ecosystem_type: str | None = None,
    ecosystem_category: str | None = None,
    ecosystem_subtype: str | None = None,
    max_records: int = 50,
) -> list[dict[str, Any]]:
    """
    Fetch NMDC biosample records from a specific ecosystem type, category, or subtype.

    Args:
        ecosystem_type (str, optional): Type of ecosystem (e.g., "Soil", "Marine")
        ecosystem_category (str, optional): Category of ecosystem
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
        return [{"error": "At least one ecosystem parameter must be provided"}]

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
        "geo_loc_name",
    ]

    records = fetch_nmdc_biosample_records_paged(
        filter_criteria=filter_criteria,
        projection=projection,
        max_records=max_records,
        verbose=True,
    )

    # Format the collection_date field to make it more readable
    for record in records:
        clean_collection_date(record)

    return records


def get_entity_by_id(entity_id: str) -> dict[str, Any]:
    """
    Retrieve any NMDC entity by its ID.

    Args:
        entity_id (str): NMDC entity ID (e.g., "nmdc:bsm-11-abc123")

    Returns:
        Dict[str, Any]: Entity data from NMDC schema API

    Examples:
        - Biosample: "nmdc:bsm-11-abc123"
        - Study: "nmdc:sty-11-xyz789"
        - OmicsProcessing: "nmdc:omprc-11-def456"
        - DataObject: "nmdc:dobj-11-ghi789"
    """
    try:
        entity_data = fetch_nmdc_entity_by_id(entity_id, verbose=True)
        return entity_data
    except Exception as e:
        return {
            "error": f"Failed to retrieve entity '{entity_id}': {str(e)}",
            "entity_id": entity_id,
        }


def get_random_biosample_subset(
    sample_count: int = 10,
    sampling_pool_size: int = 1000,
    projection: list[str] | None = None,
    filter_criteria: dict[str, Any] | None = None,
    require_coordinates: bool = True,
) -> list[dict[str, Any]]:
    """
    Get N random biosamples with configurable fields and filters.

    Args:
        sample_count (int): Number of random samples to return (default: 10)
        sampling_pool_size (int): Size of pool to sample from (default: 1000)
        projection (List[str], optional): Fields to include. If None, uses minimal set
        filter_criteria (dict, optional): MongoDB-style filters to apply
        require_coordinates (bool): Whether to require lat_lon fields (default: True)

    Returns:
        List[Dict[str, Any]]: Random biosamples with specified fields

    Examples:
        - get_random_biosample_subset(5)  # 5 random samples with coordinates
        - get_random_biosample_subset(10, projection=["id", "ecosystem_type"])
        - get_random_biosample_subset(20, require_coordinates=False)
    """
    # Use provided projection or default minimal set
    if projection is None:
        projection = ["id", "name"]
        if require_coordinates:
            projection.extend(["lat_lon", "collection_date"])

    # Build base filters
    base_filters = {}

    # Add coordinate requirements if requested
    if require_coordinates:
        coordinate_filters = {
            "lat_lon.latitude": {"$exists": True, "$ne": None},
            "lat_lon.longitude": {"$exists": True, "$ne": None},
        }
        base_filters.update(coordinate_filters)

    # Merge with user-provided filters
    if filter_criteria:
        final_filters = {**base_filters, **filter_criteria}
    else:
        final_filters = base_filters

    try:
        # Add random offset to reduce ordering bias
        random_offset = random.randint(0, min(MAX_RANDOM_OFFSET, sampling_pool_size))

        # Fetch larger pool with limited projection and random offset
        pool_records = fetch_nmdc_biosample_records_paged(
            filter_criteria=final_filters,
            projection=projection,
            max_records=sampling_pool_size + random_offset,
            verbose=True,
        )

        # Apply offset by skipping first N records
        if len(pool_records) > random_offset:
            pool_records = pool_records[random_offset:]

        if not pool_records:
            return [{"error": "No biosamples found matching criteria"}]

        # Ensure we don't try to sample more than available
        actual_sample_count = min(sample_count, len(pool_records))

        # Randomly sample from the pool
        random_samples = random.sample(pool_records, actual_sample_count)

        # Clean up collection_date format if present
        for sample in random_samples:
            clean_collection_date(sample)

        return random_samples

    except Exception as e:
        return [{"error": f"Failed to fetch random samples: {str(e)}"}]


def get_random_collection_subset(
    collection: str = "biosample_set",
    sample_count: int = 10,
    sampling_pool_size: int = 1000,
    projection: list[str] | None = None,
    filter_criteria: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Get N random records from any NMDC collection with configurable fields and filters.

    Args:
        collection (str): NMDC collection name (e.g., "biosample_set")
        sample_count (int): Number of random samples to return (default: 10)
        sampling_pool_size (int): Size of pool to sample from (default: 1000)
        projection: Fields to include. If None, uses ["id", "name"]
        filter_criteria (dict, optional): MongoDB-style filters to apply

    Returns:
        List[Dict[str, Any]]: Random records from the specified collection

    Examples:
        - get_random_collection_subset("study_set", 5)  # 5 random studies
        - get_random_collection_subset("omics_processing_set", 10)
        - get_random_collection_subset("biosample_set", 20)
    """
    # Use provided projection or default minimal set
    if projection is None:
        projection = ["id", "name"]

    try:
        # Add random offset to reduce ordering bias
        random_offset = random.randint(0, min(MAX_RANDOM_OFFSET, sampling_pool_size))

        # Fetch larger pool with limited projection and random offset
        pool_records = fetch_nmdc_collection_records_paged(
            collection=collection,
            filter_criteria=filter_criteria,
            projection=projection,
            max_records=sampling_pool_size + random_offset,
            verbose=True,
        )

        # Apply offset by skipping first N records
        if len(pool_records) > random_offset:
            pool_records = pool_records[random_offset:]

        if not pool_records:
            return [{"error": f"No records found in {collection} matching criteria"}]

        # Ensure we don't try to sample more than available
        actual_sample_count = min(sample_count, len(pool_records))

        # Randomly sample from the pool
        random_samples = random.sample(pool_records, actual_sample_count)

        # Clean up collection_date format if present (common across collections)
        for sample in random_samples:
            clean_collection_date(sample)

        return random_samples

    except Exception as e:
        return [{"error": f"Failed to fetch samples from {collection}: {str(e)}"}]
