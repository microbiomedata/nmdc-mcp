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
    fetch_nmdc_collection_names,
    fetch_nmdc_collection_records_paged,
    fetch_nmdc_collection_stats,
    fetch_nmdc_entities_by_ids_with_projection,
    fetch_nmdc_entity_by_id,
    fetch_nmdc_entity_by_id_with_projection,
)
from .constants import (
    DEFAULT_PAGE_SIZE,
    DEFAULT_RANDOM_SAMPLE_SIZE,
    LARGE_COLLECTION_THRESHOLD,
    MAX_ENTITY_IDS_PER_REQUEST,
    MAX_RANDOM_SAMPLE_SIZE,
    MIN_RANDOM_FETCH_COUNT,
    RANDOM_FETCH_MULTIPLIER,
)


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


def get_entity_by_id_with_projection(
    entity_id: str,
    collection: str,
    projection: str | list[str] | None = None,
) -> dict[str, Any]:
    """
    Retrieve a specific NMDC entity by ID with optional field projection.

    This function allows you to fetch only specific fields from a document,
    which is useful for reducing response size and focusing on relevant data.

    Args:
        entity_id (str): NMDC entity ID (e.g., "nmdc:bsm-11-abc123")
        collection (str): NMDC collection name (e.g., "biosample_set", "study_set")
        projection (str | list[str], optional): Fields to include in the response.
            Can be a comma-separated string (e.g., "id,name,ecosystem") or a list
            of field names (e.g., ["id", "name", "ecosystem"])

    Returns:
        Dict[str, Any]: Entity data with only the projected fields, or error information

    Examples:
        - get_entity_by_id_with_projection(
            "nmdc:bsm-11-abc123", "biosample_set", "id,name,ecosystem"
        )
        - get_entity_by_id_with_projection(
            "nmdc:bsm-11-abc123",
            "biosample_set",
            ["env_broad_scale", "env_local_scale", "env_medium"],
        )
    """
    try:
        entity_data = fetch_nmdc_entity_by_id_with_projection(
            entity_id=entity_id,
            collection=collection,
            projection=projection,
            verbose=True,
        )

        if entity_data is None:
            return {
                "error": f"Entity '{entity_id}' not found in collection '{collection}'",
                "entity_id": entity_id,
                "collection": collection,
            }

        return entity_data
    except Exception as e:
        return {
            "error": (
                f"Failed to retrieve entity '{entity_id}' "
                f"from '{collection}': {str(e)}"
            ),
            "entity_id": entity_id,
            "collection": collection,
        }


def get_collection_names() -> list[str]:
    """
    Get the list of available NMDC collection names.

    This tool provides information about what collections are available
    in the NMDC database. This is useful for:
    - Discovering available NMDC collections
    - Understanding what data types are available
    - Validating collection names before making other API calls

    Returns:
        List[str]: List of available collection names
            (e.g., ["biosample_set", "study_set", ...])

    Examples:
        - get_collection_names() # Get all available collection names
        - Result: ["biosample_set", "study_set", "data_object_set", ...]
    """
    try:
        collection_names = fetch_nmdc_collection_names(verbose=True)
        return collection_names
    except Exception as e:
        return [f"Error: Failed to fetch collection names: {str(e)}"]


def get_collection_stats() -> dict[str, Any]:
    """
    Get statistics for all NMDC collections including document counts.

    This tool provides information about what collections are available
    and how many documents are in each collection. This is useful for:
    - Discovering available NMDC collections
    - Understanding collection sizes for efficient sampling strategies
    - Validating that requested sample sizes don't exceed collection size

    Returns:
        Dict[str, Any]: Dictionary containing collection statistics where keys
            are collection names (e.g., "biosample_set", "study_set") and values
            contain statistics including document counts

    Examples:
        - get_collection_stats() # Get stats for all collections
        - Result: {"biosample_set": {"count": 15234}, "study_set": {"count": 543}, ...}
    """
    try:
        stats_data = fetch_nmdc_collection_stats(verbose=True)
        return stats_data
    except Exception as e:
        return {"error": f"Failed to fetch collection statistics: {str(e)}"}


def get_all_collection_ids(
    collection: str = "biosample_set",
    batch_size: int = 5000,
    max_batches: int | None = None,
) -> dict[str, Any]:
    """
    Get document IDs from a specified NMDC collection in manageable batches.

    This tool efficiently retrieves IDs from large collections by breaking them
    into smaller batches that can be processed without hitting token limits.
    Perfect for collections like biosample_set with 10,000+ documents.

    This tool is useful for:
    - Client-side random sampling from any size collection
    - Getting ID lists for analysis without memory issues
    - Efficient sampling from large collections
    - Use with get_entity_by_id() to retrieve specific documents from the ID list

    Args:
        collection (str): NMDC collection name (e.g., "biosample_set", "study_set")
        batch_size (int): Number of IDs to return per batch (default: 5000)
        max_batches (int, optional): Maximum number of batches to return
            If None, returns all available IDs in batches

    Returns:
        Dict[str, Any]: Contains batched IDs and metadata

    Examples:
        - get_all_collection_ids("biosample_set")  # Get first 5000 IDs
        - get_all_collection_ids("study_set", batch_size=100)  # Get first 100 IDs
        - get_all_collection_ids("biosample_set", max_batches=3)  # Get first 15000 IDs
    """
    try:
        # First get collection stats to understand the size
        stats = get_collection_stats()
        if collection not in stats:
            return {
                "error": f"Collection '{collection}' not found in available collections"
            }

        total_count = stats[collection].get("count", 0)

        if total_count == 0:
            return {
                "collection": collection,
                "total_count": 0,
                "batches": [],
                "note": f"Collection '{collection}' is empty.",
            }

        # Calculate effective limits
        effective_batch_size = min(batch_size, total_count)
        max_possible_batches = (
            total_count + effective_batch_size - 1
        ) // effective_batch_size

        if max_batches is None:
            # For very large collections, default to returning first batch only
            if total_count > LARGE_COLLECTION_THRESHOLD:
                effective_max_batches = 1
                note_suffix = (
                    " (Limited to first batch due to collection size. "
                    "Use max_batches to get more.)"
                )
            else:
                effective_max_batches = max_possible_batches
                note_suffix = ""
        else:
            effective_max_batches = min(max_batches, max_possible_batches)
            note_suffix = ""

        print(
            f"Fetching up to {effective_max_batches} batch(es) of "
            f"{effective_batch_size} IDs from {collection}..."
        )

        # Fetch records in batches
        batches = []
        records_fetched = 0

        for batch_num in range(effective_max_batches):
            # Calculate how many records to fetch for this batch
            remaining_in_batch = min(
                effective_batch_size, total_count - records_fetched
            )

            if remaining_in_batch <= 0:
                break

            # For batching, we need to skip records from previous batches
            skip_records = batch_num * effective_batch_size

            batch_records = fetch_nmdc_collection_records_paged(
                collection=collection,
                projection=["id"],
                max_page_size=1000,
                max_records=skip_records + remaining_in_batch,  # Fetch up to this point
                verbose=False,
            )

            # Extract IDs from this batch (skip the ones we've already processed)
            all_batch_ids = [
                record.get("id") for record in batch_records if record.get("id")
            ]
            batch_ids = all_batch_ids[skip_records : skip_records + remaining_in_batch]

            if batch_ids:
                batches.append(
                    {
                        "batch_number": batch_num + 1,
                        "ids_count": len(batch_ids),
                        "ids": batch_ids,
                    }
                )
                records_fetched += len(batch_ids)
                print(f"  Batch {batch_num + 1}: {len(batch_ids)} IDs")

            # If we got fewer records than expected, we've reached the end
            if len(all_batch_ids) < skip_records + remaining_in_batch:
                break

        return {
            "collection": collection,
            "total_count": total_count,
            "fetched_count": records_fetched,
            "batch_size": effective_batch_size,
            "batches_returned": len(batches),
            "batches": batches,
            "note": (
                f"Successfully fetched {records_fetched:,} IDs from {collection} "
                f"in {len(batches)} batch(es).{note_suffix} "
                f"Use these IDs with get_entity_by_id() for random document selection."
            ),
        }

    except Exception as e:
        return {"error": f"Failed to fetch IDs from {collection}: {str(e)}"}


def get_random_biosample_subset(
    sample_count: int = 10,
    require_coordinates: bool = True,
    projection: list[str] | None = None,
    filter_criteria: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Get a random subset of biosample records with optional filtering.

    Args:
        sample_count (int): Number of random samples to return
        require_coordinates (bool): Whether to require lat/lon coordinates
        projection (list[str], optional): Fields to include in response
        filter_criteria (dict, optional): Additional filter criteria

    Returns:
        List[Dict[str, Any]]: Random biosample records
    """
    try:
        # Build filter criteria
        filters = filter_criteria.copy() if filter_criteria else {}

        # Add coordinate requirements if needed
        if require_coordinates:
            filters.update(
                {
                    "lat_lon.latitude": {"$exists": True, "$ne": None},
                    "lat_lon.longitude": {"$exists": True, "$ne": None},
                }
            )

        # Fetch more records than needed to allow for random sampling
        fetch_count = max(
            sample_count * RANDOM_FETCH_MULTIPLIER, MIN_RANDOM_FETCH_COUNT
        )

        records = fetch_nmdc_biosample_records_paged(
            filter_criteria=filters,
            projection=projection,
            max_records=fetch_count,
            verbose=False,
        )

        if not records:
            return [{"error": "No biosamples found matching the criteria"}]

        # Random sample from the fetched records
        if len(records) <= sample_count:
            return records

        return random.sample(records, sample_count)

    except Exception as e:
        return [{"error": f"Failed to fetch random samples: {str(e)}"}]


def get_random_collection_subset(
    collection: str = "biosample_set",
    sample_count: int = 10,
    projection: list[str] | None = None,
    filter_criteria: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Get a random subset of records from any NMDC collection.

    Args:
        collection (str): NMDC collection name
        sample_count (int): Number of random samples to return
        projection (list[str], optional): Fields to include in response
        filter_criteria (dict, optional): Additional filter criteria

    Returns:
        List[Dict[str, Any]]: Random records from the collection
    """
    try:
        # Default projection for different collections
        if projection is None:
            projection = ["id", "name"]

        # Fetch more records than needed to allow for random sampling
        fetch_count = max(
            sample_count * RANDOM_FETCH_MULTIPLIER, MIN_RANDOM_FETCH_COUNT
        )

        records = fetch_nmdc_collection_records_paged(
            collection=collection,
            filter_criteria=filter_criteria,
            projection=projection,
            max_records=fetch_count,
            verbose=False,
        )

        if not records:
            return [{"error": f"No records found in {collection}"}]

        # Random sample from the fetched records
        if len(records) <= sample_count:
            return records

        return random.sample(records, sample_count)

    except Exception as e:
        return [{"error": f"Failed to fetch samples from {collection}: {str(e)}"}]


def get_random_collection_ids(
    collection: str = "biosample_set",
    sample_size: int = DEFAULT_RANDOM_SAMPLE_SIZE,
    seed: int | None = None,
) -> dict[str, Any]:
    """
    Get a random sample of document IDs from a specified NMDC collection.

    This function fetches the entire universe of IDs from a collection and then
    randomly samples from them to provide a representative subset. This is ideal
    for random sampling while staying within reasonable token limits.

    Args:
        collection (str): NMDC collection name (e.g., "biosample_set", "study_set")
        sample_size (int): Number of random IDs to return (max 1000, default 1000)
        seed (int, optional): Random seed for reproducible sampling

    Returns:
        Dict[str, Any]: Contains randomly sampled IDs and metadata

    Examples:
        - get_random_collection_ids("biosample_set")  # Get 1000 random biosample IDs
        - get_random_collection_ids(
            "study_set", sample_size=50
        )  # Get 50 random study IDs
        - get_random_collection_ids("biosample_set", seed=42)  # Reproducible sampling
    """
    try:
        # Limit sample size to prevent token overflow
        effective_sample_size = min(sample_size, MAX_RANDOM_SAMPLE_SIZE)
        if sample_size > MAX_RANDOM_SAMPLE_SIZE:
            print(
                f"Warning: sample_size limited to {MAX_RANDOM_SAMPLE_SIZE} "
                f"(requested: {sample_size})"
            )

        # Set random seed if provided
        if seed is not None:
            random.seed(seed)

        # Get collection stats to understand the size
        stats = get_collection_stats()
        if collection not in stats:
            return {
                "error": f"Collection '{collection}' not found in available collections"
            }

        total_count = stats[collection].get("count", 0)

        if total_count == 0:
            return {
                "collection": collection,
                "total_count": 0,
                "sample_size": 0,
                "sampled_ids": [],
                "note": f"Collection '{collection}' is empty.",
            }

        # If collection is smaller than requested sample, just return all IDs
        if total_count <= effective_sample_size:
            print(f"Collection has {total_count} documents, returning all IDs")
            all_records = fetch_nmdc_collection_records_paged(
                collection=collection,
                projection=["id"],
                max_page_size=1000,
                max_records=total_count,
                verbose=False,
            )
            all_ids = [record.get("id") for record in all_records if record.get("id")]
            return {
                "collection": collection,
                "total_count": total_count,
                "sample_size": len(all_ids),
                "sampled_ids": all_ids,
                "note": (
                    f"Returned all {len(all_ids)} IDs from {collection} "
                    f"(collection smaller than requested sample)."
                ),
            }

        print(
            f"Fetching all {total_count:,} IDs from {collection} for random sampling..."
        )

        # Fetch all IDs from the collection
        all_records = fetch_nmdc_collection_records_paged(
            collection=collection,
            projection=["id"],
            max_page_size=1000,
            max_records=total_count,
            verbose=False,
        )

        # Extract all IDs
        all_ids = [record.get("id") for record in all_records if record.get("id")]
        actual_count = len(all_ids)

        if actual_count == 0:
            return {
                "collection": collection,
                "total_count": total_count,
                "sample_size": 0,
                "sampled_ids": [],
                "note": f"No valid IDs found in {collection}.",
            }

        # Randomly sample from all IDs
        sampled_ids = random.sample(all_ids, min(effective_sample_size, actual_count))

        print(
            f"Randomly sampled {len(sampled_ids)} IDs from {actual_count:,} total IDs"
        )

        return {
            "collection": collection,
            "total_count": actual_count,
            "sample_size": len(sampled_ids),
            "sampled_ids": sampled_ids,
            "sampling_method": "random",
            "seed": seed,
            "note": (
                f"Randomly sampled {len(sampled_ids):,} IDs from "
                f"{actual_count:,} total IDs in {collection}. "
                f"Use these IDs with get_entity_by_id() to retrieve random documents."
            ),
        }

    except Exception as e:
        return {"error": f"Failed to fetch random IDs from {collection}: {str(e)}"}


def get_entities_by_ids_with_projection(
    entity_ids: list[str],
    collection: str,
    projection: str | list[str] | None = None,
    max_page_size: int = DEFAULT_PAGE_SIZE,
) -> dict[str, Any]:
    """
    Retrieve multiple NMDC entities by their IDs with optional field projection.

    This function allows you to fetch multiple documents at once with only specific
    fields, which is useful for reducing response size and focusing on relevant data.

    Args:
        entity_ids (list[str]): List of NMDC entity IDs
            (e.g., ["nmdc:bsm-11-abc123", "nmdc:bsm-11-def456"])
        collection (str): NMDC collection name (e.g., "biosample_set", "study_set")
        projection (str | list[str], optional): Fields to include in the response.
            Can be a comma-separated string (e.g., "id,name,ecosystem") or a list
            of field names (e.g., ["id", "name", "ecosystem"])
        max_page_size (int): Maximum number of records to retrieve per API call

    Returns:
        Dict[str, Any]: Contains the fetched entities and metadata

    Examples:
        - get_entities_by_ids_with_projection(
            ["nmdc:bsm-11-abc123", "nmdc:bsm-11-def456"],
            "biosample_set",
            "id,name,ecosystem"
        )
        - get_entities_by_ids_with_projection(
            ["nmdc:bsm-11-abc123", "nmdc:bsm-11-def456"],
            "biosample_set",
            ["env_broad_scale", "env_local_scale", "env_medium"],
        )
    """
    try:
        if not entity_ids:
            return {
                "error": "entity_ids list cannot be empty",
                "entities": [],
                "requested_count": 0,
                "fetched_count": 0,
            }

        if len(entity_ids) > MAX_ENTITY_IDS_PER_REQUEST:
            return {
                "error": (
                    f"Too many entity IDs requested. Maximum is "
                    f"{MAX_ENTITY_IDS_PER_REQUEST} per request."
                ),
                "entities": [],
                "requested_count": len(entity_ids),
                "fetched_count": 0,
            }

        entities = fetch_nmdc_entities_by_ids_with_projection(
            entity_ids=entity_ids,
            collection=collection,
            projection=projection,
            max_page_size=max_page_size,
            verbose=True,
        )

        # Create a lookup to check which IDs were found
        found_ids = {entity.get("id") for entity in entities}
        missing_ids = [
            entity_id for entity_id in entity_ids if entity_id not in found_ids
        ]

        result = {
            "collection": collection,
            "entities": entities,
            "requested_count": len(entity_ids),
            "fetched_count": len(entities),
            "requested_ids": entity_ids,
        }

        if missing_ids:
            result["missing_ids"] = missing_ids
            result["note"] = (
                f"Successfully fetched {len(entities)} out of {len(entity_ids)} "
                f"requested entities from {collection}. "
                f"{len(missing_ids)} entities were not found."
            )
        else:
            result["note"] = (
                f"Successfully fetched all {len(entities)} requested entities "
                f"from {collection}."
            )

        return result

    except Exception as e:
        return {
            "error": f"Failed to fetch entities from {collection}: {str(e)}",
            "entities": [],
            "requested_count": len(entity_ids) if entity_ids else 0,
            "fetched_count": 0,
            "collection": collection,
        }
