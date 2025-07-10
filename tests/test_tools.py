import unittest
from unittest.mock import patch

from nmdc_mcp.tools import (
    get_samples_by_ecosystem,
    get_samples_in_elevation_range,
    get_samples_within_lat_lon_bounding_box,
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


if __name__ == "__main__":
    unittest.main()
