import unittest
from unittest.mock import patch

from nmdc_mcp.tools import (
    get_biosamples_for_study,
    get_entities_by_ids_with_projection,
    get_samples_by_ecosystem,
    get_samples_in_elevation_range,
    get_samples_within_lat_lon_bounding_box,
    get_study_doi_details,
    get_study_for_biosample,
    search_studies_by_doi_criteria,
)


class TestNMDCTools(unittest.TestCase):
    """Test cases for the NMDC tools module."""

    @patch("nmdc_mcp.tools.fetch_nmdc_biosample_records_paged")
    def test_get_samples_in_elevation_range_basic(self, mock_fetch):
        """Test basic get_samples_in_elevation_range functionality."""
        # Mock the API response
        mock_fetch.return_value = [
            {"id": "sample1", "elev": 500},
            {"id": "sample2", "elev": 750},
        ]

        # Test the function
        result = get_samples_in_elevation_range(min_elevation=100, max_elevation=1000)

        # Verify the API was called correctly
        mock_fetch.assert_called_once_with(
            filter_criteria={"elev": {"$gt": 100, "$lt": 1000}},
            max_records=10,
        )

        # Verify the result
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], "sample1")
        self.assertEqual(result[1]["id"], "sample2")

    @patch("nmdc_mcp.tools.fetch_nmdc_biosample_records_paged")
    def test_get_samples_within_lat_lon_bounding_box_basic(self, mock_fetch):
        """Test basic get_samples_within_lat_lon_bounding_box functionality."""
        # Mock the API response
        mock_fetch.return_value = [
            {"id": "sample1", "lat_lon": {"latitude": 35, "longitude": -100}}
        ]

        # Test the function
        result = get_samples_within_lat_lon_bounding_box(
            lower_lat=30, upper_lat=40, lower_lon=-110, upper_lon=-90
        )

        # Verify the API was called correctly
        mock_fetch.assert_called_once_with(
            filter_criteria={
                "lat_lon.latitude": {"$gt": 30, "$lt": 40},
                "lat_lon.longitude": {"$gt": -110, "$lt": -90},
            },
            max_records=10,
        )

        # Verify the result
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "sample1")

    @patch("nmdc_mcp.tools.fetch_nmdc_biosample_records_paged")
    def test_get_samples_by_ecosystem_basic(self, mock_fetch):
        """Test basic get_samples_by_ecosystem functionality."""
        # Mock the API response
        mock_fetch.return_value = [
            {
                "id": "sample1",
                "ecosystem_type": "Soil",
                "collection_date": {"has_raw_value": "2024-01-01T00:00:00Z"},
            }
        ]

        # Test the function
        result = get_samples_by_ecosystem(ecosystem_type="Soil", max_records=25)

        # Verify the API was called correctly
        expected_projection = [
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
        mock_fetch.assert_called_once_with(
            filter_criteria={"ecosystem_type": "Soil"},
            projection=expected_projection,
            max_records=25,
            verbose=True,
        )

        # Verify the result and date formatting
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "sample1")
        self.assertEqual(result[0]["collection_date"], "2024-01-01 00:00:00 UTC")

    def test_get_samples_by_ecosystem_no_parameters(self):
        """Test get_samples_by_ecosystem with no parameters returns error."""
        result = get_samples_by_ecosystem()

        self.assertEqual(len(result), 1)
        self.assertIn("error", result[0])
        self.assertIsInstance(result[0]["error"], str)

    @patch("nmdc_mcp.tools.fetch_nmdc_biosample_records_paged")
    def test_get_samples_by_ecosystem_multiple_filters(self, mock_fetch):
        """Test get_samples_by_ecosystem with multiple filter parameters."""
        mock_fetch.return_value = []

        # Test with multiple parameters
        get_samples_by_ecosystem(
            ecosystem_type="Soil",
            ecosystem_category="Terrestrial",
            ecosystem_subtype="Agricultural",
            max_records=100,
        )

        # Verify all filters are applied
        mock_fetch.assert_called_once_with(
            filter_criteria={
                "ecosystem_type": "Soil",
                "ecosystem_category": "Terrestrial",
                "ecosystem_subtype": "Agricultural",
            },
            projection=unittest.mock.ANY,
            max_records=100,
            verbose=True,
        )

    @patch("nmdc_mcp.tools.fetch_nmdc_biosample_records_paged")
    def test_get_samples_by_ecosystem_date_formatting_error(self, mock_fetch):
        """Test date formatting handles invalid dates gracefully."""
        # Mock response with invalid date
        mock_fetch.return_value = [
            {"id": "sample1", "collection_date": {"has_raw_value": "invalid-date"}}
        ]

        result = get_samples_by_ecosystem(ecosystem_type="Soil")

        # Should keep original value if parsing fails
        self.assertEqual(result[0]["collection_date"], "invalid-date")

    @patch("nmdc_mcp.tools.fetch_nmdc_entities_by_ids_with_projection")
    def test_get_entities_by_ids_with_projection_basic(self, mock_fetch):
        """Test basic get_entities_by_ids_with_projection functionality."""
        # Mock the API response
        mock_fetch.return_value = [
            {"id": "nmdc:bsm-11-abc123", "name": "Sample 1", "ecosystem": "Soil"},
            {"id": "nmdc:bsm-11-def456", "name": "Sample 2", "ecosystem": "Marine"},
        ]

        # Test the function
        entity_ids = ["nmdc:bsm-11-abc123", "nmdc:bsm-11-def456"]
        result = get_entities_by_ids_with_projection(
            entity_ids=entity_ids,
            collection="biosample_set",
            projection="id,name,ecosystem",
        )

        # Verify the API was called correctly
        mock_fetch.assert_called_once_with(
            entity_ids=entity_ids,
            collection="biosample_set",
            projection="id,name,ecosystem",
            max_page_size=100,
            verbose=True,
        )

        # Verify the result
        self.assertEqual(result["collection"], "biosample_set")
        self.assertEqual(result["requested_count"], 2)
        self.assertEqual(result["fetched_count"], 2)
        self.assertEqual(len(result["entities"]), 2)
        self.assertEqual(result["entities"][0]["id"], "nmdc:bsm-11-abc123")
        self.assertEqual(result["entities"][1]["id"], "nmdc:bsm-11-def456")
        self.assertEqual(result["requested_ids"], entity_ids)
        self.assertNotIn("missing_ids", result)

    @patch("nmdc_mcp.tools.fetch_nmdc_entities_by_ids_with_projection")
    def test_get_entities_by_ids_with_projection_missing_entities(self, mock_fetch):
        """Test get_entities_by_ids_with_projection with some missing entities."""
        # Mock response with only one entity found
        mock_fetch.return_value = [
            {"id": "nmdc:bsm-11-abc123", "name": "Sample 1", "ecosystem": "Soil"}
        ]

        # Test with two IDs but only one found
        entity_ids = ["nmdc:bsm-11-abc123", "nmdc:bsm-11-missing"]
        result = get_entities_by_ids_with_projection(
            entity_ids=entity_ids,
            collection="biosample_set",
            projection=["id", "name", "ecosystem"],
        )

        # Verify the result shows missing entities
        self.assertEqual(result["requested_count"], 2)
        self.assertEqual(result["fetched_count"], 1)
        self.assertEqual(len(result["entities"]), 1)
        self.assertIn("missing_ids", result)
        self.assertEqual(result["missing_ids"], ["nmdc:bsm-11-missing"])
        self.assertEqual(result["requested_ids"], entity_ids)
        self.assertIn("1 entities were not found", result["note"])

    def test_get_entities_by_ids_with_projection_empty_list(self):
        """Test get_entities_by_ids_with_projection with empty entity_ids list."""
        result = get_entities_by_ids_with_projection(
            entity_ids=[], collection="biosample_set", projection="id,name"
        )

        self.assertIn("error", result)
        self.assertEqual(result["error"], "entity_ids list cannot be empty")
        self.assertEqual(result["requested_count"], 0)
        self.assertEqual(result["fetched_count"], 0)
        self.assertEqual(result["requested_ids"], [])

    def test_get_entities_by_ids_with_projection_too_many_ids(self):
        """Test get_entities_by_ids_with_projection with too many entity IDs."""
        # Create a list with more than 100 IDs
        entity_ids = [f"nmdc:bsm-11-{i:06d}" for i in range(101)]

        result = get_entities_by_ids_with_projection(
            entity_ids=entity_ids, collection="biosample_set"
        )

        self.assertIn("error", result)
        self.assertEqual(
            result["error"],
            "Too many entity IDs requested. Maximum is 100 per request.",
        )
        self.assertEqual(result["requested_count"], 101)
        self.assertEqual(result["fetched_count"], 0)
        self.assertEqual(result["requested_ids"], entity_ids)
        self.assertEqual(result["collection"], "biosample_set")

    @patch("nmdc_mcp.tools.fetch_nmdc_entities_by_ids_with_projection")
    def test_get_entities_by_ids_with_projection_api_error(self, mock_fetch):
        """Test get_entities_by_ids_with_projection handling API errors."""
        # Mock an API error
        mock_fetch.side_effect = Exception("API connection failed")

        entity_ids = ["nmdc:bsm-11-abc123"]
        result = get_entities_by_ids_with_projection(
            entity_ids=entity_ids, collection="biosample_set"
        )

        self.assertIn("error", result)
        self.assertIn("Failed to fetch entities from biosample_set", result["error"])
        self.assertIn("API connection failed", result["error"])
        self.assertEqual(result["requested_count"], 1)
        self.assertEqual(result["fetched_count"], 0)
        self.assertEqual(result["requested_ids"], entity_ids)

    def test_get_entities_by_ids_with_projection_requested_ids_none(self):
        """Test that get_entities_by_ids_with_projection raises TypeError for None."""
        # Test the case where entity_ids is explicitly None
        # Verify that the function raises a TypeError
        from nmdc_mcp.tools import get_entities_by_ids_with_projection

        # Simulate the error path where entity_ids could be None
        with self.assertRaises(TypeError):
            get_entities_by_ids_with_projection(
                entity_ids=None, collection="biosample_set"
            )

    @patch("nmdc_mcp.tools.fetch_nmdc_entity_by_id_with_projection")
    def test_get_study_doi_details_basic(self, mock_fetch):
        """Test basic get_study_doi_details functionality."""
        # Mock the API response
        mock_fetch.return_value = {
            "id": "nmdc:sty-11-abc123",
            "name": "Test Study",
            "associated_dois": [
                {
                    "doi_value": "doi:10.46936/10.25585/60001211",
                    "doi_category": "award_doi",
                    "doi_provider": "jgi",
                    "type": "nmdc:Doi",
                },
                {
                    "doi_value": "doi:10.25345/C5CC0V509",
                    "doi_category": "dataset_doi",
                    "doi_provider": "massive",
                    "type": "nmdc:Doi",
                },
            ],
        }

        # Test the function
        result = get_study_doi_details("nmdc:sty-11-abc123")

        # Verify the API was called correctly
        mock_fetch.assert_called_once_with(
            entity_id="nmdc:sty-11-abc123",
            collection="study_set",
            projection=["id", "name", "title", "associated_dois"],
            verbose=True,
        )

        # Verify the result
        self.assertEqual(result["study_id"], "nmdc:sty-11-abc123")
        self.assertEqual(result["study_name"], "Test Study")
        self.assertEqual(result["doi_count"], 2)
        self.assertEqual(len(result["associated_dois"]), 2)
        self.assertEqual(result["doi_categories_summary"]["award_doi"], 1)
        self.assertEqual(result["doi_categories_summary"]["dataset_doi"], 1)
        self.assertIn("Found 2 DOI(s)", result["note"])

    @patch("nmdc_mcp.tools.fetch_nmdc_entity_by_id_with_projection")
    def test_get_study_doi_details_no_dois(self, mock_fetch):
        """Test get_study_doi_details with study that has no DOIs."""
        # Mock response with no DOIs
        mock_fetch.return_value = {
            "id": "nmdc:sty-11-nodois",
            "name": "Study with No DOIs",
            "associated_dois": [],
        }

        result = get_study_doi_details("nmdc:sty-11-nodois")

        self.assertEqual(result["study_id"], "nmdc:sty-11-nodois")
        self.assertEqual(result["study_name"], "Study with No DOIs")
        self.assertEqual(result["doi_count"], 0)
        self.assertEqual(len(result["associated_dois"]), 0)
        self.assertIn("No DOIs found", result["note"])

    @patch("nmdc_mcp.tools.fetch_nmdc_entity_by_id_with_projection")
    def test_get_study_doi_details_study_not_found(self, mock_fetch):
        """Test get_study_doi_details with non-existent study."""
        # Mock response for not found
        mock_fetch.return_value = None

        result = get_study_doi_details("nmdc:sty-11-missing")

        self.assertIn("error", result)
        self.assertEqual(result["error"], "Study 'nmdc:sty-11-missing' not found")
        self.assertEqual(result["study_id"], "nmdc:sty-11-missing")

    @patch("nmdc_mcp.tools.fetch_nmdc_entity_by_id_with_projection")
    def test_get_study_doi_details_api_error(self, mock_fetch):
        """Test get_study_doi_details handling API errors."""
        # Mock an API error
        mock_fetch.side_effect = Exception("API connection failed")

        result = get_study_doi_details("nmdc:sty-11-abc123")

        self.assertIn("error", result)
        self.assertIn("Failed to retrieve DOI details", result["error"])
        self.assertIn("API connection failed", result["error"])
        self.assertEqual(result["study_id"], "nmdc:sty-11-abc123")

    @patch("nmdc_mcp.tools.fetch_nmdc_collection_records_paged")
    def test_search_studies_by_doi_criteria_basic(self, mock_fetch):
        """Test basic search_studies_by_doi_criteria functionality."""
        # Mock the API response with studies containing DOIs
        mock_fetch.return_value = [
            {
                "id": "nmdc:sty-11-abc123",
                "name": "Test Study 1",
                "associated_dois": [
                    {
                        "doi_value": "doi:10.25585/12345",
                        "doi_category": "dataset_doi",
                        "doi_provider": "jgi",
                        "type": "nmdc:Doi",
                    }
                ],
            },
            {
                "id": "nmdc:sty-11-def456",
                "name": "Test Study 2",
                "associated_dois": [
                    {
                        "doi_value": "doi:10.46936/67890",
                        "doi_category": "award_doi",
                        "doi_provider": "emsl",
                        "type": "nmdc:Doi",
                    }
                ],
            },
        ]

        # Test search by provider
        result = search_studies_by_doi_criteria(doi_provider="jgi")

        # Verify the API was called correctly
        mock_fetch.assert_called_once_with(
            collection="study_set",
            projection=["id", "name", "title", "associated_dois"],
            max_records=None,
            verbose=False,
        )

        # Verify the result
        self.assertEqual(len(result["matching_studies"]), 1)
        self.assertEqual(
            result["matching_studies"][0]["study_id"], "nmdc:sty-11-abc123"
        )
        self.assertEqual(result["matching_studies"][0]["matching_doi_count"], 1)
        self.assertEqual(result["search_summary"]["matching_studies_found"], 1)
        self.assertEqual(result["search_summary"]["total_matching_dois"], 1)

    @patch("nmdc_mcp.tools.fetch_nmdc_collection_records_paged")
    def test_search_studies_by_doi_criteria_combined_filters(self, mock_fetch):
        """Test search_studies_by_doi_criteria with multiple criteria."""
        # Mock response with studies having various DOI types
        mock_fetch.return_value = [
            {
                "id": "nmdc:sty-11-abc123",
                "name": "Test Study 1",
                "associated_dois": [
                    {
                        "doi_value": "doi:10.25585/12345",
                        "doi_category": "dataset_doi",
                        "doi_provider": "jgi",
                        "type": "nmdc:Doi",
                    },
                    {
                        "doi_value": "doi:10.25585/67890",
                        "doi_category": "award_doi",
                        "doi_provider": "jgi",
                        "type": "nmdc:Doi",
                    },
                ],
            }
        ]

        # Test combined search criteria
        result = search_studies_by_doi_criteria(
            doi_provider="jgi", doi_category="award_doi", doi_value_contains="10.25585"
        )

        # Should find 1 study with 1 matching DOI (award_doi from jgi containing 10.25585)  # noqa: E501
        self.assertEqual(len(result["matching_studies"]), 1)
        self.assertEqual(result["matching_studies"][0]["matching_doi_count"], 1)
        self.assertEqual(
            result["matching_studies"][0]["matching_dois"][0]["doi_category"],
            "award_doi",
        )

    def test_search_studies_by_doi_criteria_invalid_provider(self):
        """Test search_studies_by_doi_criteria with invalid provider."""
        result = search_studies_by_doi_criteria(doi_provider="invalid_provider")

        self.assertIn("error", result)
        self.assertIn("Invalid doi_provider", result["error"])
        self.assertIn("invalid_provider", result["error"])

    def test_search_studies_by_doi_criteria_invalid_category(self):
        """Test search_studies_by_doi_criteria with invalid category."""
        result = search_studies_by_doi_criteria(doi_category="invalid_category")

        self.assertIn("error", result)
        self.assertIn("Invalid doi_category", result["error"])
        self.assertIn("invalid_category", result["error"])

    def test_search_studies_by_doi_criteria_no_criteria(self):
        """Test search_studies_by_doi_criteria with no search criteria."""
        result = search_studies_by_doi_criteria()

        self.assertIn("error", result)
        self.assertEqual(
            result["error"], "At least one search criterion must be provided"
        )

    @patch("nmdc_mcp.tools.fetch_nmdc_collection_records_paged")
    def test_search_studies_by_doi_criteria_no_matches(self, mock_fetch):
        """Test search_studies_by_doi_criteria when no matches are found."""
        # Mock response with studies that don't match criteria
        mock_fetch.return_value = [
            {
                "id": "nmdc:sty-11-abc123",
                "name": "Test Study 1",
                "associated_dois": [
                    {
                        "doi_value": "doi:10.25585/12345",
                        "doi_category": "dataset_doi",
                        "doi_provider": "jgi",
                        "type": "nmdc:Doi",
                    }
                ],
            }
        ]

        # Search for provider that doesn't exist in data
        result = search_studies_by_doi_criteria(doi_provider="zenodo")

        self.assertEqual(len(result["matching_studies"]), 0)
        self.assertEqual(result["search_summary"]["matching_studies_found"], 0)
        self.assertIn("No studies found", result["note"])

    @patch("nmdc_mcp.tools.fetch_nmdc_collection_records_paged")
    def test_search_studies_by_doi_criteria_api_error(self, mock_fetch):
        """Test search_studies_by_doi_criteria handling API errors."""
        # Mock an API error
        mock_fetch.side_effect = Exception("API connection failed")

        result = search_studies_by_doi_criteria(doi_provider="jgi")

        self.assertIn("error", result)
        self.assertIn("Failed to search studies by DOI criteria", result["error"])
        self.assertIn("API connection failed", result["error"])

    @patch("nmdc_mcp.tools.get_entity_by_id")
    @patch("nmdc_mcp.tools.get_entity_by_id_with_projection")
    def test_get_study_for_biosample_success(
        self, mock_get_with_projection, mock_get_entity
    ):
        """Test successful retrieval of study for biosample."""
        # Mock biosample data with associated study
        mock_get_with_projection.return_value = {
            "id": "nmdc:bsm-11-abc123",
            "name": "Test Biosample",
            "associated_studies": ["nmdc:sty-11-xyz789"],
        }

        # Mock study data
        mock_get_entity.return_value = {
            "id": "nmdc:sty-11-xyz789",
            "name": "Test Study",
            "description": "A test study",
        }

        result = get_study_for_biosample("nmdc:bsm-11-abc123")

        # Verify function calls
        mock_get_with_projection.assert_called_once_with(
            entity_id="nmdc:bsm-11-abc123",
            collection="biosample_set",
            projection=["id", "name", "associated_studies"],
        )
        mock_get_entity.assert_called_once_with("nmdc:sty-11-xyz789")

        # Verify result
        self.assertEqual(result["biosample_id"], "nmdc:bsm-11-abc123")
        self.assertEqual(result["biosample_name"], "Test Biosample")
        self.assertEqual(result["study_id"], "nmdc:sty-11-xyz789")
        self.assertEqual(result["study"]["name"], "Test Study")
        self.assertIn("Successfully found study", result["note"])

    @patch("nmdc_mcp.tools.get_entity_by_id_with_projection")
    def test_get_study_for_biosample_no_associated_studies(
        self, mock_get_with_projection
    ):
        """Test handling biosample with no associated studies."""
        # Mock biosample data without associated studies
        mock_get_with_projection.return_value = {
            "id": "nmdc:bsm-11-abc123",
            "name": "Test Biosample",
            "associated_studies": [],
        }

        result = get_study_for_biosample("nmdc:bsm-11-abc123")

        # Verify result
        self.assertEqual(result["biosample_id"], "nmdc:bsm-11-abc123")
        self.assertEqual(result["biosample_name"], "Test Biosample")
        self.assertIsNone(result["study"])
        self.assertIn("No associated studies found", result["note"])

    @patch("nmdc_mcp.tools.get_entity_by_id")
    @patch("nmdc_mcp.tools.get_entity_by_id_with_projection")
    def test_get_study_for_biosample_multiple_studies(
        self, mock_get_with_projection, mock_get_entity
    ):
        """Test handling biosample with multiple associated studies."""
        # Mock biosample data with multiple associated studies
        mock_get_with_projection.return_value = {
            "id": "nmdc:bsm-11-abc123",
            "name": "Test Biosample",
            "associated_studies": ["nmdc:sty-11-xyz789", "nmdc:sty-11-def456"],
        }

        # Mock study data (only first study is fetched)
        mock_get_entity.return_value = {
            "id": "nmdc:sty-11-xyz789",
            "name": "Primary Study",
        }

        result = get_study_for_biosample("nmdc:bsm-11-abc123")

        # Verify only first study is fetched
        mock_get_entity.assert_called_once_with("nmdc:sty-11-xyz789")

        # Verify result includes additional study IDs
        self.assertEqual(result["study_id"], "nmdc:sty-11-xyz789")
        self.assertEqual(result["additional_study_ids"], ["nmdc:sty-11-def456"])
        self.assertIn("1 additional study found", result["note"])

    @patch("nmdc_mcp.tools.get_entity_by_id_with_projection")
    def test_get_study_for_biosample_biosample_not_found(
        self, mock_get_with_projection
    ):
        """Test handling when biosample is not found."""
        # Mock error response for biosample lookup
        mock_get_with_projection.return_value = {
            "error": "Entity 'nmdc:bsm-11-missing' not found"
        }

        result = get_study_for_biosample("nmdc:bsm-11-missing")

        # Verify error is passed through
        self.assertIn("error", result)

    @patch("nmdc_mcp.tools.get_entity_by_id")
    @patch("nmdc_mcp.tools.get_entity_by_id_with_projection")
    def test_get_study_for_biosample_study_not_found(
        self, mock_get_with_projection, mock_get_entity
    ):
        """Test handling when study is not found."""
        # Mock biosample data with associated study
        mock_get_with_projection.return_value = {
            "id": "nmdc:bsm-11-abc123",
            "name": "Test Biosample",
            "associated_studies": ["nmdc:sty-11-missing"],
        }

        # Mock error response for study lookup
        mock_get_entity.return_value = {"error": "Study not found"}

        result = get_study_for_biosample("nmdc:bsm-11-abc123")

        # Verify error handling
        self.assertEqual(result["biosample_id"], "nmdc:bsm-11-abc123")
        self.assertEqual(result["study_id"], "nmdc:sty-11-missing")
        self.assertIsNone(result["study"])
        self.assertIn("error", result)
        self.assertIn("Failed to retrieve study", result["error"])

    @patch("nmdc_mcp.tools.fetch_nmdc_biosample_records_paged")
    @patch("nmdc_mcp.tools.get_entity_by_id_with_projection")
    def test_get_biosamples_for_study_success(
        self, mock_get_with_projection, mock_fetch_biosamples
    ):
        """Test successful retrieval of biosample IDs for a study."""
        # Mock study data
        mock_get_with_projection.return_value = {
            "id": "nmdc:sty-11-xyz789",
            "name": "Test Study",
        }

        # Mock biosample data (only IDs since that's all we return now)
        mock_biosamples = [
            {"id": "nmdc:bsm-11-abc123"},
            {"id": "nmdc:bsm-11-def456"},
        ]
        mock_fetch_biosamples.return_value = mock_biosamples

        result = get_biosamples_for_study("nmdc:sty-11-xyz789")

        # Verify correct API calls
        mock_get_with_projection.assert_called_once_with(
            entity_id="nmdc:sty-11-xyz789",
            collection="study_set",
            projection=["id", "name"],
        )
        mock_fetch_biosamples.assert_called_once()

        # Verify result structure
        self.assertEqual(result["study_id"], "nmdc:sty-11-xyz789")
        self.assertEqual(result["study_name"], "Test Study")
        self.assertEqual(result["biosample_ids"], mock_biosamples)
        self.assertEqual(result["biosample_count"], 2)
        self.assertEqual(result["max_records"], 50)
        self.assertEqual(result["potentially_truncated"], False)
        self.assertIn("Found 2 biosample IDs", result["note"])

    @patch("nmdc_mcp.tools.get_entity_by_id_with_projection")
    def test_get_biosamples_for_study_study_not_found(self, mock_get_with_projection):
        """Test handling when study is not found."""
        # Mock error response for study lookup
        mock_get_with_projection.return_value = {"error": "Study not found"}

        result = get_biosamples_for_study("nmdc:sty-11-missing")

        # Verify error handling
        self.assertEqual(result["study_id"], "nmdc:sty-11-missing")
        self.assertEqual(result["study_name"], "")
        self.assertEqual(result["biosample_ids"], [])
        self.assertEqual(result["biosample_count"], 0)
        self.assertEqual(result["max_records"], 50)
        self.assertEqual(result["potentially_truncated"], False)
        self.assertIn("error", result)
        self.assertIn("Study nmdc:sty-11-missing not found", result["error"])

    @patch("nmdc_mcp.tools.get_entity_by_id_with_projection")
    def test_get_biosamples_for_study_exception(self, mock_get_with_projection):
        """Test handling when an exception occurs."""
        # Mock exception
        mock_get_with_projection.side_effect = Exception("Database connection error")

        result = get_biosamples_for_study("nmdc:sty-11-xyz789")

        # Verify exception handling
        self.assertEqual(result["study_id"], "nmdc:sty-11-xyz789")
        self.assertEqual(result["study_name"], "")
        self.assertEqual(result["biosample_ids"], [])
        self.assertEqual(result["biosample_count"], 0)
        self.assertEqual(result["max_records"], 50)
        self.assertEqual(result["potentially_truncated"], False)
        self.assertIn("error", result)
        self.assertIn("Failed to get biosamples for study", result["error"])
        self.assertIn("Database connection error", result["error"])

    @patch("nmdc_mcp.tools.fetch_nmdc_biosample_records_paged")
    @patch("nmdc_mcp.tools.get_entity_by_id_with_projection")
    def test_get_biosamples_for_study_truncation_warning(
        self, mock_get_with_projection, mock_fetch_biosamples
    ):
        """Test truncation warning when max_records limit is reached."""
        # Mock study data
        mock_get_with_projection.return_value = {
            "id": "nmdc:sty-11-xyz789",
            "name": "Test Study",
        }

        # Mock biosample data that equals max_records (indicating potential truncation)
        mock_biosamples = [{"id": f"nmdc:bsm-11-{i:03d}"} for i in range(10)]
        mock_fetch_biosamples.return_value = mock_biosamples

        result = get_biosamples_for_study("nmdc:sty-11-xyz789", max_records=10)

        # Verify result structure includes truncation warning
        self.assertEqual(result["study_id"], "nmdc:sty-11-xyz789")
        self.assertEqual(result["study_name"], "Test Study")
        self.assertEqual(result["biosample_count"], 10)
        self.assertEqual(result["max_records"], 10)
        self.assertEqual(result["potentially_truncated"], True)
        self.assertIn("limited to max_records=10", result["note"])
        self.assertIn("there may be more results", result["note"])


if __name__ == "__main__":
    unittest.main()
