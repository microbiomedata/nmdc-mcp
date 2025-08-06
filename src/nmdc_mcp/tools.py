################################################################################
# nmdc_mcp/tools.py
# This module contains tools that consume the generic API wrapper functions in
# nmdc_mcp/api.py and constrain/transform them based on use cases/applications
################################################################################
import logging
import random
import requests
from datetime import datetime
from typing import Any, List, Dict

from .api import (
    fetch_functional_annotation_records,
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

# Create logger for this module
logger = logging.getLogger(__name__)


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


def get_data_objects_by_pfam_domains(
    pfam_domain_ids: list[str],
    biosample_limit: int = 100,
) -> dict[str, Any]:
    """
    Get data objects from biosamples containing ALL specified PFAM domains.

    This tool searches the NMDC database for biosamples that contain all the specified
    PFAM domains (using AND logic) and returns a structured response similar to the
    bacterial-pfam-clean.json format, with minimal activity information and rich
    output file metadata.

    Args:
        pfam_domain_ids (list[str]): List of PFAM domain identifiers WITHOUT the
            "PFAM:" prefix. Examples: ["PF00005", "PF00072"] for ABC transporter
            and response regulator domains.
        biosample_limit (int): Maximum number of biosamples to return. Default is 100.
            Higher values may result in larger responses and longer processing times.

    Returns:
        dict[str, Any]: Structured response containing:
            - search_criteria: Details about the domains searched and limits applied
            - biosample_count: Total biosamples available matching the criteria
            - samples: List of biosample records with activities and data objects

    Examples:
        # Search for biosamples with ABC transporter domain
        get_data_objects_by_pfam_domains(["PF00005"])

        # Search for samples with both ABC transporter and response regulator
        get_data_objects_by_pfam_domains(["PF00005", "PF00072"], biosample_limit=50)

        # Search for samples with multiple metabolic domains
        get_data_objects_by_pfam_domains(["PF00001", "PF00106", "PF00107"])
    """
    try:
        # Validate input
        if not pfam_domain_ids:
            return {
                "error": "pfam_domain_ids parameter is required and cannot be empty",
                "search_criteria": {
                    "pfam_domains": pfam_domain_ids,
                    "biosample_limit": biosample_limit
                }
            }

        if not isinstance(pfam_domain_ids, list):
            return {
                "error": "pfam_domain_ids must be a list of PFAM domain identifiers",
                "search_criteria": {
                    "pfam_domains": pfam_domain_ids,
                    "biosample_limit": biosample_limit
                }
            }

        # Validate and add PFAM: prefix to domain IDs if not present
        processed_pfam_ids = []
        for domain_id in pfam_domain_ids:
            if not isinstance(domain_id, str):
                return {
                    "error": f"Invalid PFAM domain ID: {domain_id}. Must be a string.",
                    "search_criteria": {
                        "pfam_domains": pfam_domain_ids,
                        "biosample_limit": biosample_limit
                    }
                }

            # Add PFAM: prefix if not present
            if domain_id.startswith("PFAM:"):
                processed_pfam_ids.append(domain_id)
            else:
                processed_pfam_ids.append(f"PFAM:{domain_id}")

        # Build filter criteria with AND logic for multiple PFAM domains
        conditions = []
        for pfam_id in processed_pfam_ids:
            conditions.append({
                "op": "==",
                "field": "id",
                "value": pfam_id,
                "table": "pfam_function"
            })

        filter_criteria = {"conditions": conditions}

        # Make the API call directly to get both count and results
        import requests
        import json
        
        base_url = "https://data.microbiomedata.org/api/biosample/search"
        url = f"{base_url}?limit={biosample_limit}"
        
        payload = {
            "conditions": conditions
        }
        
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        
        total_count = data.get("count", 0)
        biosample_records = data.get("results", [])

        if not biosample_records:
            return {
                "search_criteria": {
                    "pfam_domains": pfam_domain_ids,
                    "biosample_limit": biosample_limit
                },
                "total_biosamples_available": total_count,
                "biosample_count": 0,
                "samples": [],
                "message": (
                    "No biosamples found containing all PFAM domains: "
                    f"{', '.join(processed_pfam_ids)}"
                )
            }

        # Process each biosample to extract data objects in the target format
        samples = []

        for biosample in biosample_records:
            biosample_id = biosample.get("id", "")
            study_id = biosample.get("study_id", "")

            # Extract activities and their outputs from omics_processing
            activities = []
            omics_processing = biosample.get("omics_processing", [])

            for omics in omics_processing:
                # Extract omics_data entries as activities
                omics_data_list = omics.get("omics_data", [])

                for omics_data in omics_data_list:
                    activity = {
                        "activity_id": omics_data.get("id"),
                        "activity_type": omics_data.get("type"),
                        "analysis_category": omics_data.get(
                            "metaproteomics_analysis_category"
                        ),
                        "informed_by": [
                            {
                                "id": informed.get("id"),
                                "type": informed.get("annotations", {}).get("type"),
                                "omics_type": informed.get("annotations", {}).get(
                                    "omics_type"
                                )
                            }
                            for informed in omics_data.get("was_informed_by", [])
                        ],
                        "outputs": [
                            {
                                "id": output.get("id"),
                                "name": output.get("name"),
                                "description": output.get("description"),
                                "file_type": output.get("file_type"),
                                "file_type_description": output.get(
                                    "file_type_description"
                                ),
                                "file_size_bytes": output.get("file_size_bytes"),
                                "md5_checksum": output.get("md5_checksum"),
                                "url": output.get("url"),
                                "downloads": output.get("downloads"),
                                "selected": output.get("selected")
                            }
                            for output in omics_data.get("outputs", [])
                        ]
                    }
                    activities.append(activity)

            sample_record = {
                "biosample_id": biosample_id,
                "study_id": study_id,
                "activities": activities
            }
            samples.append(sample_record)

        return {
            "search_criteria": {
                "pfam_domains": pfam_domain_ids,
                "biosample_limit": biosample_limit
            },
            "total_biosamples_available": total_count,
            "biosample_count": len(samples),
            "samples": samples
        }

    except Exception as e:
        return {
            "error": f"Failed to get data objects by PFAM domains: {str(e)}",
            "search_criteria": {
                "pfam_domains": pfam_domain_ids,
                "biosample_limit": biosample_limit
            }
        }






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
                f"Failed to retrieve entity '{entity_id}' from '{collection}': {str(e)}"
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
                "Use these IDs with get_entity_by_id() for random document selection."
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
                    "(collection smaller than requested sample)."
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
                "Use these IDs with get_entity_by_id() to retrieve random documents."
            ),
        }

    except Exception as e:
        return {"error": f"Failed to fetch random IDs from {collection}: {str(e)}"}


def get_study_for_biosample(biosample_id: str) -> dict[str, Any]:
    """
    Get the study associated with a specific biosample.

    Args:
        biosample_id (str): NMDC biosample ID (e.g., "nmdc:bsm-11-abc123")

    Returns:
        Dict[str, Any]: Dictionary containing the study information and metadata.
            Possible keys include:
            - biosample_id (str): The input biosample ID
            - biosample_name (str): Name of the biosample (empty string if unavailable)
            - study_id (str | None): ID of the associated study
            - study (dict | None): Complete study data object
            - error (str): Error message (only present if an error occurred)
            - note (str): Human-readable summary of the operation
            - additional_study_ids (list[str]): Additional study IDs if multiple found

    Examples:
        - get_study_for_biosample("nmdc:bsm-11-abc123")
    """
    try:
        # Get the biosample with only the id and associated_studies fields
        biosample_data = get_entity_by_id_with_projection(
            entity_id=biosample_id,
            collection="biosample_set",
            projection=["id", "name", "associated_studies"],
        )

        if "error" in biosample_data:
            return {
                "biosample_id": biosample_id,
                "error": biosample_data.get("error", "Unknown error"),
                "note": f"Failed to retrieve biosample {biosample_id}",
            }

        associated_studies = biosample_data.get("associated_studies", [])

        if not associated_studies:
            return {
                "biosample_id": biosample_id,
                "biosample_name": biosample_data.get("name", ""),
                "study_id": None,
                "study": None,
                "note": f"No associated studies found for biosample {biosample_id}",
            }

        # Get the first (and typically only) associated study
        study_id = associated_studies[0]
        study_data = get_entity_by_id(study_id)

        if "error" in study_data:
            return {
                "biosample_id": biosample_id,
                "biosample_name": biosample_data.get("name", ""),
                "study_id": study_id,
                "study": None,
                "error": (
                    f"Failed to retrieve study {study_id}: "
                    f"{study_data.get('error', 'Unknown error')}"
                ),
            }

        result = {
            "biosample_id": biosample_id,
            "biosample_name": biosample_data.get("name", ""),
            "study_id": study_id,
            "study": study_data,
            "note": f"Successfully found study {study_id} for biosample {biosample_id}",
        }

        # If there are multiple associated studies, include them in the response
        if len(associated_studies) > 1:
            result["additional_study_ids"] = associated_studies[1:]
            result["note"] += (
                f" (Note: {len(associated_studies)-1} additional "
                f"{'study' if len(associated_studies) == 2 else 'studies'} found)"
            )

        return result

    except Exception as e:
        return {
            "biosample_id": biosample_id,
            "biosample_name": "",
            "study_id": None,
            "study": None,
            "error": f"Failed to get study for biosample {biosample_id}: {str(e)}",
            "note": (
                f"Error occurred while retrieving study for biosample {biosample_id}"
            ),
        }


def get_biosamples_for_study(study_id: str, max_records: int = 50) -> dict[str, Any]:
    """
    Get biosample IDs associated with a specific study.

    Args:
        study_id (str): NMDC study ID (e.g., "nmdc:sty-11-xyz789")
        max_records (int): Maximum number of biosample IDs to return

    Returns:
        Dict[str, Any]: Dictionary containing the biosample IDs and metadata
            - study_id (str): The requested study ID
            - study_name (str): Name of the study (empty if not found)
            - biosample_ids (list): List of biosample ID dictionaries
            - biosample_count (int): Number of biosample IDs returned
            - max_records (int): The limit that was applied
            - potentially_truncated (bool): True if results may be incomplete
            - note (str): Human-readable summary
            - error (str): Error message (only present if error occurred)

    Examples:
        - get_biosamples_for_study("nmdc:sty-11-xyz789")
        - get_biosamples_for_study("nmdc:sty-11-xyz789", max_records=100)

        Example return:
        {
            "study_id": "nmdc:sty-11-xyz789",
            "study_name": "Example Study",
            "biosample_ids": [
                {"id": "nmdc:bsm-11-abc123"},
                {"id": "nmdc:bsm-11-def456"}
            ],
            "biosample_count": 2,
            "max_records": 50,
            "potentially_truncated": False,
            "note": "Found 2 biosample IDs associated with study nmdc:sty-11-xyz789"
        }
    """
    try:
        # First verify the study exists
        study_data = get_entity_by_id_with_projection(
            entity_id=study_id,
            collection="study_set",
            projection=["id", "name"],
        )

        if "error" in study_data:
            return {
                "study_id": study_id,
                "study_name": "",
                "biosample_ids": [],
                "biosample_count": 0,
                "max_records": max_records,
                "potentially_truncated": False,
                "error": (
                    f"Study {study_id} not found: "
                    f"{study_data.get('error', 'Unknown error')}"
                ),
                "note": f"Failed to retrieve study {study_id}",
            }

        # Search for biosamples that have this study in their associated_studies field
        filter_criteria = {"associated_studies": study_id}

        projection = ["id"]

        biosample_ids = fetch_nmdc_biosample_records_paged(
            filter_criteria=filter_criteria,
            projection=projection,
            max_records=max_records,
            verbose=True,
        )

        # Check if results may have been truncated
        note = (
            f"Found {len(biosample_ids)} biosample IDs associated with study {study_id}"
        )
        potentially_truncated = len(biosample_ids) == max_records
        if potentially_truncated:
            note += (
                f" (limited to max_records={max_records}; there may be more results)"
            )
            logging.warning(
                "Potential truncation in get_biosamples_for_study: "
                f"returned {len(biosample_ids)} IDs for study {study_id}, "
                f"may be more results beyond max_records={max_records}"
            )

        return {
            "study_id": study_id,
            "study_name": study_data.get("name", ""),
            "biosample_ids": biosample_ids,
            "biosample_count": len(biosample_ids),
            "max_records": max_records,
            "potentially_truncated": potentially_truncated,
            "note": note,
        }

    except Exception as e:
        return {
            "study_id": study_id,
            "study_name": "",
            "biosample_ids": [],
            "biosample_count": 0,
            "max_records": max_records,
            "potentially_truncated": False,
            "error": f"Failed to get biosample IDs for study {study_id}: {str(e)}",
            "note": (
                f"Error occurred while retrieving biosample IDs for study {study_id}"
            ),
        }


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

    Raises:
        TypeError: If entity_ids is None

    Returns:
        Dict[str, Any]: Contains the fetched entities and metadata including:
            - entities: List of fetched entity documents
            - requested_count: Number of entity IDs requested
            - fetched_count: Number of entities successfully fetched
            - requested_ids: List of entity IDs that were requested
            - missing_ids: List of entity IDs that were not found
              (only present if some IDs are missing)
            - collection: Name of the collection queried
            - error: Error message (only present if an error occurred)
            - note: Human-readable summary of the operation

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
    if entity_ids is None:
        raise TypeError("entity_ids cannot be None")

    try:
        if not entity_ids:
            return {
                "error": "entity_ids list cannot be empty",
                "entities": [],
                "requested_count": 0,
                "fetched_count": 0,
                "requested_ids": [],
                "collection": collection,
            }

        if len(entity_ids) > MAX_ENTITY_IDS_PER_REQUEST:
            return {
                "error": (
                    "Too many entity IDs requested. Maximum is "
                    f"{MAX_ENTITY_IDS_PER_REQUEST} per request."
                ),
                "entities": [],
                "requested_count": len(entity_ids),
                "fetched_count": 0,
                "requested_ids": entity_ids,
                "collection": collection,
            }

        entities = fetch_nmdc_entities_by_ids_with_projection(
            entity_ids=entity_ids,
            collection=collection,
            projection=projection,
            max_page_size=max_page_size,
            verbose=True,
        )

        # Create a lookup to check which IDs were found
        entity_map = {entity.get("id"): entity for entity in entities}
        reordered_entities = [
            entity_map.get(entity_id)
            for entity_id in entity_ids
            if entity_map.get(entity_id)
        ]
        missing_ids = [
            entity_id for entity_id in entity_ids if entity_id not in entity_map
        ]

        result = {
            "collection": collection,
            "entities": reordered_entities,
            "requested_count": len(entity_ids),
            "fetched_count": len(reordered_entities),
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
            "requested_ids": entity_ids if entity_ids else [],
        }


def get_study_doi_details(study_id: str) -> dict[str, Any]:
    """
    Get the details of all DOIs associated with a specific study.

    This function retrieves the complete DOI information for a given study,
    including DOI values, categories, and providers.

    Args:
        study_id (str): NMDC study ID (e.g., "nmdc:sty-11-abc123")

    Returns:
        Dict[str, Any]: Dictionary containing study information and associated DOI
            details

    Examples:
        - get_study_doi_details("nmdc:sty-11-abc123")
        - Result: {
            "study_id": "nmdc:sty-11-abc123",
            "study_name": "Study Name",
            "doi_count": 2,
            "associated_dois": [
                {
                    "doi_value": "doi:10.46936/10.25585/60001211",
                    "doi_category": "award_doi",
                    "doi_provider": "jgi",
                    "type": "nmdc:Doi"
                },
                ...
            ]
        }
    """
    try:
        # Fetch the study entity with projection to get only relevant fields
        study_data = fetch_nmdc_entity_by_id_with_projection(
            entity_id=study_id,
            collection="study_set",
            projection=["id", "name", "title", "associated_dois"],
            verbose=True,
        )

        if study_data is None:
            return {
                "error": f"Study '{study_id}' not found",
                "study_id": study_id,
            }

        # Extract DOI information
        associated_dois = study_data.get("associated_dois", [])

        # Build the response
        result = {
            "study_id": study_data.get("id", study_id),
            "study_name": study_data.get("name", study_data.get("title", "Unknown")),
            "doi_count": len(associated_dois),
            "associated_dois": associated_dois,
        }

        if not associated_dois:
            result["note"] = f"No DOIs found for study '{study_id}'"
        else:
            # Add summary of DOI categories
            doi_categories: dict[str, int] = {}
            for doi in associated_dois:
                category = doi.get("doi_category", "unknown")
                doi_categories[category] = doi_categories.get(category, 0) + 1

            result["doi_categories_summary"] = doi_categories
            result["note"] = (
                f"Found {len(associated_dois)} DOI(s) for study '{study_id}': "
                f"{', '.join(f'{count} {category}' for category, count in doi_categories.items())}"  # noqa: E501
            )

        return result

    except Exception as e:
        return {
            "error": f"Failed to retrieve DOI details for study '{study_id}': {str(e)}",
            "study_id": study_id,
        }




def search_studies_by_doi_criteria(
    doi_provider: str | None = None,
    doi_category: str | None = None,
    doi_value_contains: str | None = None,
    max_results: int = 50,
) -> dict[str, Any]:
    """
    Search for studies that have DOIs matching specified criteria.

    This function searches through all studies to find those with DOIs that match
    the given criteria. Useful for finding studies from specific providers, categories,
    or DOI patterns.

    Args:
        doi_provider (str, optional): Filter by DOI provider. Valid values:
            emsl, jgi, kbase, osti, ess_dive, massive, gsc, zenodo, edi, figshare
        doi_category (str, optional): Filter by DOI category. Valid values:
            award_doi, dataset_doi, publication_doi, data_management_plan_doi
        doi_value_contains (str, optional): Filter DOIs containing this substring
        max_results (int): Maximum number of studies to return (default: 50)

    Returns:
        Dict[str, Any]: Dictionary containing matching studies and their DOI information

    Examples:
        - search_studies_by_doi_criteria(doi_provider="jgi")
        - search_studies_by_doi_criteria(doi_category="dataset_doi", max_results=10)
        - search_studies_by_doi_criteria(doi_value_contains="10.25585")
        - search_studies_by_doi_criteria(doi_provider="emsl", doi_category="award_doi")
    """
    try:
        # Validate inputs
        valid_providers = {
            "emsl",
            "jgi",
            "kbase",
            "osti",
            "ess_dive",
            "massive",
            "gsc",
            "zenodo",
            "edi",
            "figshare",
        }
        valid_categories = {
            "award_doi",
            "dataset_doi",
            "publication_doi",
            "data_management_plan_doi",
        }

        if doi_provider and doi_provider not in valid_providers:
            return {
                "error": (  # noqa: E501
                    f"Invalid doi_provider '{doi_provider}'. Valid values:"
                    f" {sorted(valid_providers)}"
                ),
                "search_criteria": {
                    "doi_provider": doi_provider,
                    "doi_category": doi_category,
                    "doi_value_contains": doi_value_contains,
                },
            }

        if doi_category and doi_category not in valid_categories:
            return {
                "error": (  # noqa: E501
                    f"Invalid doi_category '{doi_category}'. Valid values:"
                    f" {sorted(valid_categories)}"
                ),
                "search_criteria": {
                    "doi_provider": doi_provider,
                    "doi_category": doi_category,
                    "doi_value_contains": doi_value_contains,
                },
            }

        if not any([doi_provider, doi_category, doi_value_contains]):
            return {
                "error": "At least one search criterion must be provided",
                "search_criteria": {
                    "doi_provider": doi_provider,
                    "doi_category": doi_category,
                    "doi_value_contains": doi_value_contains,
                },
            }

        # Fetch all studies with their DOI information
        studies_with_dois = fetch_nmdc_collection_records_paged(
            collection="study_set",
            projection=["id", "name", "title", "associated_dois"],
            max_records=None,  # Get all studies to search through
            verbose=False,
        )

        matching_studies = []
        total_studies_checked = 0
        studies_with_dois_count = 0

        for study in studies_with_dois:
            total_studies_checked += 1
            associated_dois = study.get("associated_dois", [])

            if not associated_dois:
                continue

            studies_with_dois_count += 1

            # Check if any DOI in this study matches our criteria
            matching_dois = []
            for doi in associated_dois:
                # Check provider criteria
                if doi_provider and doi.get("doi_provider") != doi_provider:
                    continue

                # Check category criteria
                if doi_category and doi.get("doi_category") != doi_category:
                    continue

                # Check value contains criteria
                if doi_value_contains and doi_value_contains not in doi.get(
                    "doi_value", ""
                ):
                    continue

                # If we reach here, this DOI matches all criteria
                matching_dois.append(doi)

            # If we found matching DOIs in this study, add it to results
            if matching_dois:
                study_result = {
                    "study_id": study.get("id"),
                    "study_name": study.get("name", study.get("title", "Unknown")),
                    "matching_dois": matching_dois,
                    "matching_doi_count": len(matching_dois),
                    "total_doi_count": len(associated_dois),
                }
                matching_studies.append(study_result)

                # Stop if we've reached max_results
                if len(matching_studies) >= max_results:
                    break

        # Build summary statistics
        total_matching_dois = sum(
            study["matching_doi_count"] for study in matching_studies
        )

        # Generate search criteria summary
        criteria_parts = []
        if doi_provider:
            criteria_parts.append(f"provider={doi_provider}")
        if doi_category:
            criteria_parts.append(f"category={doi_category}")
        if doi_value_contains:
            criteria_parts.append(f"value_contains='{doi_value_contains}'")
        criteria_summary = ", ".join(criteria_parts)

        result = {
            "search_criteria": {
                "doi_provider": doi_provider,
                "doi_category": doi_category,
                "doi_value_contains": doi_value_contains,
            },
            "search_summary": {
                "criteria": criteria_summary,
                "total_studies_checked": total_studies_checked,
                "studies_with_dois": studies_with_dois_count,
                "matching_studies_found": len(matching_studies),
                "total_matching_dois": total_matching_dois,
                "max_results_limit": max_results,
                "results_truncated": len(matching_studies) >= max_results,
            },
            "matching_studies": matching_studies,
        }

        if matching_studies:
            result["note"] = (
                f"Found {len(matching_studies)} studies with DOIs matching criteria ({criteria_summary}). "  # noqa: E501
                f"Total of {total_matching_dois} matching DOIs across all studies."
            )
        else:
            result["note"] = (
                f"No studies found with DOIs matching criteria ({criteria_summary}). "
                f"Searched {studies_with_dois_count} studies that have DOIs."
            )

        return result

    except Exception as e:
        return {
            "error": f"Failed to search studies by DOI criteria: {str(e)}",
            "search_criteria": {
                "doi_provider": doi_provider,
                "doi_category": doi_category,
                "doi_value_contains": doi_value_contains,
            },
        }


def fetch_and_filter_gff_by_pfam_domains(
    data_object_id: str,
    pfam_domain_ids: List[str],
    max_rows: int = 1000,
    sample_bytes: int = 5000000,
) -> Dict[str, Any]:
    """
    Fetch data object metadata and filter GFF content for specified PFAM domains.
    
    This tool takes a data object ID, resolves it to a download URL via the NMDC runtime API,
    downloads the GFF file content (with optional byte limiting), and filters for rows 
    containing any of the specified PFAM domains.
    
    Args:
        data_object_id (str): NMDC data object ID (e.g., "nmdc:dobj-11-abc123")
        pfam_domain_ids (List[str]): List of PFAM domain identifiers to search for.
            Examples: ["PF04183", "PF06276"], ["PF00005", "PF00072"]
            These will be matched case-insensitively in GFF annotation fields.
        max_rows (int): Maximum number of matching rows to return (default: 1000).
            This prevents context overflow from very large result sets.
        sample_bytes (int): Maximum bytes to download from GFF file (default: 5MB).
            This prevents downloading entire large files when only samples are needed.
    
    Returns:
        Dict[str, Any]: Structured response containing:
            - data_object_metadata: Complete metadata from runtime API including download URL
            - search_criteria: Details about domains searched and limits applied  
            - file_info: Information about the downloaded content
            - matching_annotations: Filtered GFF rows containing the PFAM domains
            - summary: Statistics about processing and matches found
    
    Examples:
        # Basic PFAM filtering for a data object
        fetch_and_filter_gff_by_pfam_domains(
            "nmdc:dobj-11-abc123", 
            ["PF04183", "PF06276"]
        )
        
        # Limited sampling with specific row limit
        fetch_and_filter_gff_by_pfam_domains(
            "nmdc:dobj-11-def456",
            ["PF00005"],
            max_rows=500,
            sample_bytes=1000000  # 1MB sample
        )
    """
    try:
        # Validate inputs
        if not data_object_id:
            return {
                "error": "data_object_id parameter is required and cannot be empty",
                "search_criteria": {
                    "data_object_id": data_object_id,
                    "pfam_domains": pfam_domain_ids,
                    "max_rows": max_rows,
                    "sample_bytes": sample_bytes
                }
            }
            
        if not pfam_domain_ids:
            return {
                "error": "pfam_domain_ids parameter is required and cannot be empty",
                "search_criteria": {
                    "data_object_id": data_object_id,
                    "pfam_domains": pfam_domain_ids,
                    "max_rows": max_rows,
                    "sample_bytes": sample_bytes
                }
            }

        # Step 1: Fetch data object metadata from runtime API
        runtime_api_url = f"https://api.microbiomedata.org/data_objects/{data_object_id.replace(':', '%3A')}"
        
        logger.info(f"Fetching metadata for data object: {data_object_id}")
        metadata_response = requests.get(runtime_api_url, headers={"Accept": "application/json"})
        metadata_response.raise_for_status()
        
        data_object_metadata = metadata_response.json()
        download_url = data_object_metadata.get('url')
        
        if not download_url:
            return {
                "error": "No download URL found in data object metadata",
                "data_object_metadata": data_object_metadata,
                "search_criteria": {
                    "data_object_id": data_object_id,
                    "pfam_domains": pfam_domain_ids,
                    "max_rows": max_rows,
                    "sample_bytes": sample_bytes
                }
            }

        # Step 2: Download GFF content (with byte limiting)
        logger.info(f"Downloading GFF content from: {download_url}")
        headers = {}
        if sample_bytes > 0:
            headers["Range"] = f"bytes=0-{sample_bytes-1}"
            
        content_response = requests.get(download_url, headers=headers, timeout=30)
        content_response.raise_for_status()
        
        # Get actual bytes downloaded
        content_length = len(content_response.content)
        was_truncated = content_length >= sample_bytes
        
        # Step 3: Parse and filter GFF content
        content = content_response.text
        lines = content.strip().split('\n')
        
        # Normalize PFAM domain IDs for case-insensitive matching
        normalized_pfams = [pfam.upper() for pfam in pfam_domain_ids]
        
        matching_annotations = []
        total_rows = 0
        
        for line in lines:
            # Skip empty lines and comments
            if not line.strip() or line.startswith('#'):
                continue
                
            total_rows += 1
            
            # Check if line contains any PFAM domain (case-insensitive)
            line_upper = line.upper()
            if any(pfam in line_upper for pfam in normalized_pfams):
                # Parse the GFF line into components
                try:
                    parts = line.split('\t')
                    if len(parts) >= 9:  # Standard GFF format has 9 columns
                        annotation = {
                            "seqname": parts[0],
                            "source": parts[1], 
                            "feature": parts[2],
                            "start": parts[3],
                            "end": parts[4],
                            "score": parts[5],
                            "strand": parts[6],
                            "frame": parts[7],
                            "attributes": parts[8],
                            "raw_line": line
                        }
                        matching_annotations.append(annotation)
                    else:
                        # For non-standard format, just store the raw line
                        matching_annotations.append({"raw_line": line})
                except Exception as parse_error:
                    # If parsing fails, store raw line with error note
                    matching_annotations.append({
                        "raw_line": line,
                        "parse_error": str(parse_error)
                    })
                
                # Limit rows to prevent context overflow
                if len(matching_annotations) >= max_rows:
                    break
        
        # Build response
        file_info = {
            "download_url": download_url,
            "content_length_bytes": content_length,
            "sample_bytes_requested": sample_bytes,
            "was_truncated": was_truncated,
            "total_rows_processed": total_rows,
            "matching_rows_found": len(matching_annotations),
            "max_rows_applied": len(matching_annotations) >= max_rows
        }
        
        summary = {
            "data_object_id": data_object_id,
            "pfam_domains_searched": pfam_domain_ids,
            "total_matching_annotations": len(matching_annotations),
            "file_size_bytes": content_length,
            "processing_limits": {
                "max_rows": max_rows,
                "sample_bytes": sample_bytes
            }
        }
        
        result = {
            "data_object_metadata": data_object_metadata,
            "search_criteria": {
                "data_object_id": data_object_id,
                "pfam_domains": pfam_domain_ids,
                "max_rows": max_rows,
                "sample_bytes": sample_bytes
            },
            "file_info": file_info,
            "matching_annotations": matching_annotations,
            "summary": summary
        }
        
        if matching_annotations:
            result["note"] = (
                f"Successfully processed data object {data_object_id} and found "
                f"{len(matching_annotations)} annotations containing PFAM domains: "
                f"{', '.join(pfam_domain_ids)}"
            )
        else:
            result["note"] = (
                f"Processed data object {data_object_id} but found no annotations "
                f"containing PFAM domains: {', '.join(pfam_domain_ids)}"
            )
            
        return result
        
    except requests.exceptions.RequestException as e:
        return {
            "error": f"Failed to fetch data or download content: {str(e)}",
            "search_criteria": {
                "data_object_id": data_object_id,
                "pfam_domains": pfam_domain_ids,
                "max_rows": max_rows,
                "sample_bytes": sample_bytes
            }
        }
    except Exception as e:
        return {
            "error": f"Failed to process GFF content: {str(e)}",
            "search_criteria": {
                "data_object_id": data_object_id,
                "pfam_domains": pfam_domain_ids,
                "max_rows": max_rows,
                "sample_bytes": sample_bytes
            }
        }


