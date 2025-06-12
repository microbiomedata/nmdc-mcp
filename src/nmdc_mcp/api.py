################################################################################
# nmdc_mcp/api.py
# This module contains wrapper functions that interact with endpoints in the
# NMDC API suite
# TODO: Instead of using the requests library to make HTTP calls directly,
# we should use the https://github.com/microbiomedata/nmdc_api_utilities package
# so that we are not duplicating code that already exists in the NMDC ecosystem.
################################################################################
import json
from typing import Any, Dict, List, Optional, Union
import requests


def fetch_nmdc_biosample_records_paged(
    max_page_size: int = 100,
    projection: Optional[Union[str, List[str]]] = None,
    page_token: Optional[str] = None,
    filter_criteria: Optional[
        Dict[str, Any]
    ] = None,  # Placeholder for future filtering support
    additional_params: Optional[Dict[str, Any]] = None,
    max_records: Optional[int] = None,
    verbose: bool = False,
) -> List[Dict[str, Any]]:
    """
    This function retrieves biosample records from the NMDC API, handling pagination
    automatically to return the complete set of results.

    Args:
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
        A list of dictionaries, where each dictionary represents a biosample record.
    """
    base_url: str = "https://api.microbiomedata.org/nmdcschema"
    collection: str = "biosample_set"

    all_records = []
    endpoint_url = f"{base_url}/{collection}"
    params = {"max_page_size": max_page_size}

    if projection:
        if isinstance(projection, list):
            params["projection"] = ",".join(projection)
        else:
            params["projection"] = projection

    if page_token:
        params["page_token"] = page_token

    if filter_criteria:
        params["filter"] = json.dumps(filter_criteria)
        pass

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


def fetch_metagenomic_analyses_paged(
    max_page_size: int = 100,
    projection: Optional[Union[str, List[str]]] = None,
    page_token: Optional[str] = None,
    filter_criteria: Optional[Dict[str, Any]] = None,
    additional_params: Optional[Dict[str, Any]] = None,
    max_records: Optional[int] = None,
    verbose: bool = False,
) -> List[Dict[str, Any]]:
    """
    Retrieves metagenomic analysis records from the NMDC API, handling pagination
    automatically to return the complete set of results.

    Args:
        max_page_size: Maximum number of records to retrieve per API call.
        projection: Fields to include in the response. Can be a comma-separated string
            or a list of field names.
        page_token: Token for retrieving a specific page of results.
        filter_criteria: MongoDB-style query dictionary for filtering results.
        additional_params: Additional query parameters to include in the API request.
        max_records: Maximum total number of records to retrieve across all pages.
        verbose: If True, print progress information during retrieval.

    Returns:
        A list of dictionaries, where each dictionary represents a metagenomic analysis record.
    """
    base_url: str = "https://api.microbiomedata.org/nmdcschema"
    collection: str = "metagenome_annotation_set"  # Collection for metagenomic analyses

    all_records = []
    endpoint_url = f"{base_url}/{collection}"
    params = {"max_page_size": max_page_size}

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


def fetch_taxa_abundance_data(
    sample_id: Optional[str] = None,
    taxon_id: Optional[str] = None,
    taxonomy_level: Optional[str] = None,
    min_abundance: Optional[float] = None,
    max_records: Optional[int] = None,
    verbose: bool = False,
) -> List[Dict[str, Any]]:
    """
    Retrieves taxonomic abundance data from metagenomic analyses in the NMDC database.

    Args:
        sample_id: Optional biosample ID to filter by a specific sample
        taxon_id: Optional taxon ID (e.g., NCBI taxonomy ID) to filter for a specific taxon
        taxonomy_level: Optional taxonomic level (e.g., 'phylum', 'class', 'genus', 'species')
        min_abundance: Optional minimum relative abundance threshold
        max_records: Maximum total number of records to retrieve
        verbose: If True, print progress information during retrieval

    Returns:
        A list of dictionaries containing taxonomic abundance data
    """
    filter_criteria = {}
    
    if sample_id:
        filter_criteria["has_input.id"] = sample_id
        
    if taxon_id:
        filter_criteria["has_taxon.id"] = taxon_id
        
    if taxonomy_level:
        filter_criteria["taxon_rank"] = taxonomy_level
        
    if min_abundance:
        filter_criteria["abundance"] = {"$gte": min_abundance}
    
    # Project only the fields we need for taxonomic analysis
    projection = [
        "id", 
        "name",
        "has_input.id",
        "has_input.name",
        "has_taxon",
        "taxon_rank",
        "abundance"
    ]
    
    records = fetch_metagenomic_analyses_paged(
        filter_criteria=filter_criteria,
        projection=projection,
        max_records=max_records,
        verbose=verbose
    )
    
    return records
