import unittest

import pytest

from nmdc_mcp.tools import (
    get_samples_by_annotation,
    get_samples_by_ecosystem,
    get_samples_in_elevation_range,
    get_samples_within_lat_lon_bounding_box,
)


class TestNMDCIntegration(unittest.TestCase):
    """Integration tests that hit the real NMDC API.

    These tests validate actual behavior against the live service.
    They focus on structure and behavior rather than specific counts
    since the database evolves over time.
    """

    @pytest.mark.integration
    def test_get_samples_by_ecosystem_real_api(self):
        """Test get_samples_by_ecosystem with real API call."""
        # Test with a common ecosystem type
        results = get_samples_by_ecosystem(ecosystem_type="Soil", max_records=3)

        # Validate structure
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0, "Should find some soil samples")
        self.assertLessEqual(len(results), 3, "Should respect max_records limit")

        # Validate each result has expected structure
        for result in results:
            self.assertIsInstance(result, dict)
            # Should have basic required fields
            self.assertIn("id", result)

            # Validate field types
            if result.get("id"):
                self.assertIsInstance(result["id"], str)
            if result.get("name"):
                self.assertIsInstance(result["name"], str)
            if result.get("ecosystem_type"):
                self.assertEqual(result["ecosystem_type"], "Soil")

    @pytest.mark.integration
    def test_get_samples_by_ecosystem_error_handling(self):
        """Test error handling when no parameters provided."""
        results = get_samples_by_ecosystem()

        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 1)
        self.assertIn("error", results[0])
        self.assertIsInstance(results[0]["error"], str)

    @pytest.mark.integration
    def test_get_samples_in_elevation_range_real_api(self):
        """Test get_samples_in_elevation_range with real API call."""
        # Test with a reasonable elevation range
        results = get_samples_in_elevation_range(min_elevation=0, max_elevation=1000)

        # Validate structure
        self.assertIsInstance(results, list)
        # Note: might return empty if no samples in this range
        self.assertLessEqual(len(results), 10, "Should respect default max_records")

        # If we have results, validate structure
        for result in results:
            self.assertIsInstance(result, dict)
            self.assertIn("id", result)

    @pytest.mark.integration
    def test_get_samples_within_lat_lon_bounding_box_real_api(self):
        """Test get_samples_within_lat_lon_bounding_box with real API call."""
        # Test with a bounding box around continental US
        results = get_samples_within_lat_lon_bounding_box(
            lower_lat=25, upper_lat=50, lower_lon=-125, upper_lon=-65
        )

        # Validate structure
        self.assertIsInstance(results, list)
        self.assertLessEqual(len(results), 10, "Should respect default max_records")

        # If we have results, validate structure
        for result in results:
            self.assertIsInstance(result, dict)
            self.assertIn("id", result)

    @pytest.mark.integration
    def test_ecosystem_categories_variety(self):
        """Test different ecosystem categories work."""
        # Use smaller, more reliable ecosystems to avoid API timeouts
        # Marine ecosystem queries can be very large and cause 524 timeouts
        test_ecosystems = ["Soil", "Freshwater"]

        for ecosystem in test_ecosystems:
            with self.subTest(ecosystem=ecosystem):
                try:
                    results = get_samples_by_ecosystem(
                        ecosystem_type=ecosystem, max_records=2
                    )
                    self.assertIsInstance(results, list)
                    # Some ecosystems might not have samples, that's ok
                    if len(results) > 0 and "error" not in results[0]:
                        # If we have real results, validate structure
                        for result in results:
                            self.assertIsInstance(result, dict)
                            self.assertIn("id", result)
                except Exception as e:
                    # If API times out or fails, skip this ecosystem
                    self.skipTest(f"API timeout/error for {ecosystem}: {str(e)}")

    @pytest.mark.integration
    def test_get_samples_by_annotation(self):
        """Simple test for get_samples_by_annotation with basic validation."""
        results = get_samples_by_annotation(
            gene_function_id="KEGG.ORTHOLOGY:K00001", max_records=1
        )
        
        # Basic validation
        self.assertIsInstance(results, dict)    
        self.assertIn("samples", results)
        self.assertIn("total_biosamples_available", results)
        self.assertIn("biosample_count", results)
        
        self.assertIsInstance(results["samples"], list)
        self.assertIsInstance(results["samples"][0], dict)
        self.assertIn("biosample_id", results["samples"][0])
        self.assertIn("study_id", results["samples"][0])
        self.assertIn("activities", results["samples"][0])
        self.assertIsInstance(results["samples"][0]["activities"], list)



if __name__ == "__main__":
    unittest.main()
