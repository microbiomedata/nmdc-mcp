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


def fetch_nmdc_collection_records_paged(
    collection: str = "biosample_set",
    max_page_size: int = 100,
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


def fetch_nmdc_biosample_records_paged(
    max_page_size: int = 100,
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
