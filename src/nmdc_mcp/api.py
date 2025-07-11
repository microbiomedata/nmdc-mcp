################################################################################
# nmdc_mcp/api.py
# This module contains wrapper functions that interact with endpoints in the
# NMDC API suite
# TODO: Instead of using the requests library to make HTTP calls directly,
# we should use the https://github.com/microbiomedata/nmdc_api_utilities package
# so that we are not duplicating code that already exists in the NMDC ecosystem.
################################################################################
import json
from typing import Any

import requests

from .constants import DEFAULT_PAGE_SIZE


def fetch_nmdc_collection_records_paged(
    collection: str = "biosample_set",
    max_page_size: int = DEFAULT_PAGE_SIZE,
    projection: str | list[str] | None = None,
    page_token: str | None = None,
    filter_criteria: dict[str, Any] | None = None,  # Future filtering support
    additional_params: dict[str, Any] | None = None,
    max_records: int | None = None,
    verbose: bool = False,
) -> list[dict[str, Any]]:
    """
    This function retrieves records from any NMDC collection, handling pagination
    automatically to return the complete set of results.

    Args:
        collection: NMDC collection name (e.g., "biosample_set", "study_set")
        max_page_size: Maximum number of records to retrieve per API call.
        projection: Fields to include in the response. Can be a comma-separated string
            or a list of field names.
        page_token: Token for retrieving a specific page of results, typically
            obtained from a previous response.
        filter_criteria: MongoDB-style query dictionary for filtering results.
        additional_params: Additional query parameters to include in the API request.
        max_records: Maximum total number of records to retrieve across all pages.
        verbose: If True, print progress information during retrieval.

    Returns:
        A list of dictionaries, each representing a record from the collection.
    """
    base_url: str = "https://api.microbiomedata.org/nmdcschema"

    all_records = []
    endpoint_url = f"{base_url}/{collection}"
    params: dict[str, Any] = {"max_page_size": max_page_size}

    if projection:
        if isinstance(projection, list):
            params["projection"] = ",".join(projection)
        else:
            params["projection"] = projection

    if page_token:
        params["page_token"] = page_token

    if filter_criteria:
        params["filter"] = json.dumps(filter_criteria)

    if additional_params:
        params.update(additional_params)

    while True:
        response = requests.get(endpoint_url, params=params)
        response.raise_for_status()
        data = response.json()

        records = data.get("resources", [])
        all_records.extend(records)

        if verbose:
            print(f"Fetched {len(records)} records; total so far: {len(all_records)}")

        # Check if we've hit the max_records limit
        if max_records is not None and len(all_records) >= max_records:
            all_records = all_records[:max_records]
            if verbose:
                print(f"Reached max_records limit: {max_records}. Stopping fetch.")
            break

        next_page_token = data.get("next_page_token")
        if next_page_token:
            params["page_token"] = next_page_token
        else:
            break

    return all_records


def fetch_nmdc_entity_by_id(
    entity_id: str,
    base_url: str = "https://api.microbiomedata.org/nmdcschema",
    verbose: bool = False,
) -> dict[str, Any]:
    """
    Fetch any NMDC schema entity by its ID.

    Args:
        entity_id: NMDC ID (e.g., "nmdc:bsm-11-abc123", "nmdc:sty-11-xyz789")
        base_url: Base URL for NMDC schema API
        verbose: Enable verbose logging

    Returns:
        Dictionary containing the entity data

    Raises:
        requests.HTTPError: If the entity is not found or API request fails
    """
    endpoint_url = f"{base_url}/ids/{entity_id}"

    if verbose:
        print(f"Fetching entity from: {endpoint_url}")

    response = requests.get(endpoint_url)
    response.raise_for_status()

    entity_data = response.json()

    if verbose:
        print(f"Retrieved entity: {entity_data.get('id', 'Unknown ID')}")

    return entity_data  # type: ignore[no-any-return]


def fetch_nmdc_collection_names(
    base_url: str = "https://api.microbiomedata.org/nmdcschema",
    verbose: bool = False,
) -> list[str]:
    """
    Fetch the list of available NMDC collection names.

    Args:
        base_url: Base URL for NMDC schema API
        verbose: Enable verbose logging

    Returns:
        List of collection names

    Raises:
        requests.HTTPError: If the API request fails
    """
    endpoint_url = f"{base_url}/collection_names"

    if verbose:
        print(f"Fetching collection names from: {endpoint_url}")

    response = requests.get(endpoint_url)
    response.raise_for_status()

    collection_names = response.json()

    if verbose:
        print(f"Retrieved {len(collection_names)} collection names: {collection_names}")

    return collection_names


def fetch_nmdc_collection_stats(
    base_url: str = "https://api.microbiomedata.org/nmdcschema",
    verbose: bool = False,
) -> dict[str, Any]:
    """
    Fetch statistics for all NMDC collections including document counts.

    Args:
        base_url: Base URL for NMDC schema API
        verbose: Enable verbose logging

    Returns:
        Dictionary containing collection statistics with counts for each collection

    Raises:
        requests.HTTPError: If the API request fails
    """
    endpoint_url = f"{base_url}/collection_stats"

    if verbose:
        print(f"Fetching collection stats from: {endpoint_url}")

    response = requests.get(endpoint_url)
    response.raise_for_status()

    raw_stats = response.json()

    # Transform the response format from list to dictionary keyed by collection name
    stats_data = {}

    for collection_stat in raw_stats:
        # Extract collection name from namespace
        # (e.g., "nmdc.biosample_set" -> "biosample_set")
        ns = collection_stat.get("ns", "")
        if ns.startswith("nmdc."):
            collection_name = ns[5:]  # Remove "nmdc." prefix
            storage_stats = collection_stat.get("storageStats", {})

            stats_data[collection_name] = {
                "count": storage_stats.get("count", 0),
                "size_bytes": storage_stats.get("size", 0),
                "avg_obj_size": storage_stats.get("avgObjSize", 0),
                "storage_size": storage_stats.get("storageSize", 0),
                "total_size": storage_stats.get("totalSize", 0),
            }

            if verbose:
                count = storage_stats.get("count", 0)
                print(f"  {collection_name}: {count:,} documents")

    if verbose:
        total_collections = len(stats_data)
        print(f"Retrieved stats for {total_collections} collections")

    return stats_data


def fetch_nmdc_entity_by_id_with_projection(
    entity_id: str,
    collection: str,
    projection: str | list[str] | None = None,
    base_url: str = "https://api.microbiomedata.org/nmdcschema",
    verbose: bool = False,
) -> dict[str, Any] | None:
    """
    Fetch a specific NMDC entity by ID with optional field projection.

    This function uses the collection-specific endpoint with filtering to fetch
    a single document, allowing for field projection unlike the generic /ids/ endpoint.

    Args:
        entity_id: NMDC ID (e.g., "nmdc:bsm-11-abc123")
        collection: NMDC collection name (e.g., "biosample_set", "study_set")
        projection: Fields to include in the response. Can be a comma-separated string
            or a list of field names.
        base_url: Base URL for NMDC schema API
        verbose: Enable verbose logging

    Returns:
        Dictionary containing the entity data with projected fields,
        or None if not found

    Raises:
        requests.HTTPError: If the API request fails
    """
    filter_criteria = {"id": entity_id}

    records = fetch_nmdc_collection_records_paged(
        collection=collection,
        max_page_size=1,
        projection=projection,
        filter_criteria=filter_criteria,
        max_records=1,
        verbose=verbose,
    )

    if records:
        return records[0]
    return None


def fetch_nmdc_entities_by_ids_with_projection(
    entity_ids: list[str],
    collection: str,
    projection: str | list[str] | None = None,
    max_page_size: int = DEFAULT_PAGE_SIZE,
    base_url: str = "https://api.microbiomedata.org/nmdcschema",
    verbose: bool = False,
) -> list[dict[str, Any]]:
    """
    Fetch multiple NMDC entities by their IDs with optional field projection.

    This function uses the collection-specific endpoint with filtering to fetch
    multiple documents by ID, allowing for field projection.

    Args:
        entity_ids: List of NMDC IDs
            (e.g., ["nmdc:bsm-11-abc123", "nmdc:bsm-11-def456"])
        collection: NMDC collection name (e.g., "biosample_set", "study_set")
        projection: Fields to include in the response. Can be a comma-separated string
            or a list of field names.
        max_page_size: Maximum number of records to retrieve per API call
        base_url: Base URL for NMDC schema API
        verbose: Enable verbose logging

    Returns:
        List of dictionaries containing the entity data with projected fields

    Raises:
        requests.HTTPError: If the API request fails
    """
    if not entity_ids:
        return []

    # Use MongoDB $in operator to filter by multiple IDs
    filter_criteria = {"id": {"$in": entity_ids}}

    if verbose:
        print(
            f"Fetching {len(entity_ids)} entities from {collection} "
            f"with filter: {filter_criteria}"
        )

    records = fetch_nmdc_collection_records_paged(
        collection=collection,
        max_page_size=max_page_size,
        projection=projection,
        filter_criteria=filter_criteria,
        max_records=len(entity_ids),  # Limit to the number of IDs requested
        verbose=verbose,
    )

    if verbose:
        print(f"Retrieved {len(records)} entities from {collection}")

    return records


def fetch_nmdc_biosample_records_paged(
    max_page_size: int = DEFAULT_PAGE_SIZE,
    projection: str | list[str] | None = None,
    page_token: str | None = None,
    filter_criteria: dict[str, Any] | None = None,
    additional_params: dict[str, Any] | None = None,
    max_records: int | None = None,
    verbose: bool = False,
) -> list[dict[str, Any]]:
    """
    Backwards-compatible wrapper for fetching biosample records.
    This is a convenience function that calls fetch_nmdc_collection_records_paged
    with collection="biosample_set".
    """
    return fetch_nmdc_collection_records_paged(
        collection="biosample_set",
        max_page_size=max_page_size,
        projection=projection,
        page_token=page_token,
        filter_criteria=filter_criteria,
        additional_params=additional_params,
        max_records=max_records,
        verbose=verbose,
    )
