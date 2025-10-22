################################################################################
# nmdc_mcp/api.py
# This module contains wrapper functions that interact with endpoints in the
# NMDC API suite
# TODO: Instead of using the requests library to make HTTP calls directly,
# we should use the https://github.com/microbiomedata/nmdc_api_utilities package
# so that we are not duplicating code that already exists in the NMDC ecosystem.
################################################################################
import json
import os
from typing import Any

import requests

from .constants import BASE_URL, DEFAULT_PAGE_SIZE


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
    base_url: str = "api-backup.microbiomedata.org/nmdcschema"

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
    base_url: str = "api-backup.microbiomedata.org/nmdcschema",
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
    base_url: str = "api-backup.microbiomedata.org/nmdcschema",
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
    base_url: str = "api-backup.microbiomedata.org/nmdcschema",
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
    base_url: str = "api-backup.microbiomedata.org/nmdcschema",
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
    base_url: str = "api-backup.microbiomedata.org/nmdcschema",
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


def fetch_functional_annotation_records(
    filter_criteria: list[dict] | None = None,
    conditions: list[dict] | None = None,
    limit: int | None = None,
    offset: int = 0,
    base_url: str = "https://data.microbiomedata.org/api/biosample/search",
    verbose: bool = False,
) -> dict[str, Any]:
    """
    Fetch biosample records that have specific functional annotations.

    This function queries the data.microbiomedata.org/api/biosample/search endpoint
    to retrieve biosample records that match functional annotation criteria.

    Args:
        filter_criteria: data object filter criteria for the search
        conditions: list of conditions for which to search under
        limit: Maximum number of records to retrieve
        base_url: Base URL for the biosample search API
        verbose: Enable verbose logging

    Returns:
        Dictionary containing the API response with biosample records

    Raises:
        requests.HTTPError: If the API request fails
    """
    if filter_criteria is None:
        filter_criteria = []
    if conditions is None:
        conditions = []

    # Prepare the request payload
    payload: dict[str, Any] = {
        "data_object_filter": filter_criteria,
        "conditions": conditions,
    }

    if limit is not None:
        url = f"{base_url}?limit={limit}"
    else:
        url = base_url

    if offset > 0:
        url += f"&offset={offset}"

    if verbose:
        print(f"Fetching functional annotation records from: {url}")
        print(f"Payload: {json.dumps(payload, indent=2)}")

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()

        data = response.json()
        num_results = len(data.get("results", []))

        if verbose:
            print(f"Retrieved {num_results} functional annotation records")

        return data

    except requests.exceptions.RequestException as e:
        if verbose:
            print(f"Error fetching functional annotation records: {str(e)}")
        raise


def fetch_study_data_objects(
    study_id: str,
    base_url: str = "https://api-dev.microbiomedata.org/data_objects/study",
    verbose: bool = False,
) -> list[dict[str, Any]]:
    """
    Fetch data objects for a specific study using the NMDC runtime API.

    This function queries the runtime API endpoint to retrieve all data objects
    (including biosample relationships) associated with a given study.

    Args:
        study_id: NMDC study ID (e.g., "nmdc:sty-11-abc123")
        base_url: Base URL for the runtime API data objects endpoint
        verbose: Enable verbose logging

    Returns:
        List of dictionaries containing biosample and data object information
        Each dictionary has keys: "biosample_id" and "data_objects" (list)

    Raises:
        requests.HTTPError: If the API request fails
    """
    url = f"{base_url}/{study_id}"

    if verbose:
        print(f"Fetching study data objects from: {url}")

    try:
        response = requests.get(url)
        response.raise_for_status()

        data = response.json()

        # The API returns a list of dictionaries with biosample_id and data_objects
        if isinstance(data, list):
            records = data
        else:
            # Handle case where response might be wrapped in another structure
            records = data.get("results", data.get("data", []))

        if verbose:
            print(
                f"Retrieved data objects for {len(records)} biosamples in "
                f"study {study_id}"
            )

        return records

    except requests.exceptions.RequestException as e:
        if verbose:
            print(f"Error fetching study data objects: {str(e)}")
        raise


def run_aggregation_queries(
    query: dict, token: str, allow_broken_refs: bool = False
) -> dict:
    """
    Run a MongoDB compatible aggregation query via the NMDC API. The endpoint
    preforms find, aggregate, update, delete, and getMore commands for users
    that have adequate permissions.

    Args:
        query: a dictionary that contains the MongoDB compatible query.
        token: bearer token to authorize the request.
        allow_broken_refs: boolean to determine if the query being run should
            allow for broken references in the database.

    Returns:
        The API response

    Raises:
        requests.HTTPError: If the API request fails
    """
    env_token = os.getenv("TOKEN")
    if env_token:
        token = env_token
    params = {"allow_broken_refs": allow_broken_refs}
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    url = f"{BASE_URL}/queries:run"
    try:
        response = requests.post(url, params=params, data=query, headers=headers)
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        print("An error calling the API occured:\n", e)
        raise
