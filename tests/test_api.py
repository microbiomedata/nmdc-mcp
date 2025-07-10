from unittest.mock import Mock, patch

import pytest

from nmdc_mcp.api import (
    fetch_nmdc_biosample_records_paged,
)
from nmdc_mcp.tools import (
    clean_collection_date,
    get_random_biosample_subset,
    get_random_collection_subset,
)


@pytest.fixture
def mock_response():
    mock_resp = Mock()
    mock_resp.json.return_value = {
        "resources": [{"id": "sample1"}, {"id": "sample2"}],
        "next_page_token": None,
    }
    mock_resp.raise_for_status.return_value = None
    return mock_resp


def test_fetch_nmdc_biosample_records_paged(mock_response):
    with patch("requests.get", return_value=mock_response):
        results = fetch_nmdc_biosample_records_paged(max_page_size=10)

    assert len(results) == 2
    assert results[0]["id"] == "sample1"
    assert results[1]["id"] == "sample2"


class TestCleanCollectionDate:
    """Test the clean_collection_date helper function."""

    def test_clean_collection_date_with_valid_date(self):
        record = {
            "id": "test",
            "collection_date": {"has_raw_value": "2023-01-15T10:30:00Z"},
        }
        clean_collection_date(record)
        assert record["collection_date"] == "2023-01-15 10:30:00 UTC"

    def test_clean_collection_date_with_invalid_date(self):
        record = {"id": "test", "collection_date": {"has_raw_value": "invalid-date"}}
        clean_collection_date(record)
        assert record["collection_date"] == "invalid-date"

    def test_clean_collection_date_no_date_field(self):
        record = {"id": "test"}
        clean_collection_date(record)
        assert "collection_date" not in record

    def test_clean_collection_date_already_string(self):
        record = {"id": "test", "collection_date": "2023-01-15"}
        clean_collection_date(record)
        assert record["collection_date"] == "2023-01-15"


class TestGetRandomBiosampleSubset:
    """Test the get_random_biosample_subset function."""

    @patch("nmdc_mcp.tools.fetch_nmdc_biosample_records_paged")
    @patch("nmdc_mcp.tools.random.randint")
    @patch("nmdc_mcp.tools.random.sample")
    def test_get_random_biosample_subset_basic(
        self, mock_sample, mock_randint, mock_fetch
    ):
        # Setup mocks
        mock_randint.return_value = 5
        mock_records = [
            {"id": f"sample{i}", "lat_lon": {"latitude": 1.0, "longitude": 2.0}}
            for i in range(10)
        ]
        mock_fetch.return_value = mock_records
        mock_sample.return_value = mock_records[:3]

        # Call function
        result = get_random_biosample_subset(sample_count=3)

        # Assertions
        assert len(result) == 3
        mock_fetch.assert_called_once()
        mock_sample.assert_called_once()

    @patch("nmdc_mcp.tools.fetch_nmdc_biosample_records_paged")
    def test_get_random_biosample_subset_empty_pool(self, mock_fetch):
        mock_fetch.return_value = []

        result = get_random_biosample_subset(sample_count=5)

        assert len(result) == 1
        assert "error" in result[0]
        assert "No biosamples found" in result[0]["error"]

    @patch("nmdc_mcp.tools.fetch_nmdc_biosample_records_paged")
    def test_get_random_biosample_subset_with_projection(self, mock_fetch):
        mock_fetch.return_value = [{"id": "sample1", "ecosystem_type": "Soil"}]

        get_random_biosample_subset(sample_count=1, projection=["id", "ecosystem_type"])

        # Check that projection was passed correctly
        args, kwargs = mock_fetch.call_args
        assert "projection" in kwargs
        assert kwargs["projection"] == ["id", "ecosystem_type"]

    @patch("nmdc_mcp.tools.fetch_nmdc_biosample_records_paged")
    def test_get_random_biosample_subset_without_coordinates(self, mock_fetch):
        mock_fetch.return_value = [{"id": "sample1", "name": "test"}]

        get_random_biosample_subset(sample_count=1, require_coordinates=False)

        # Check that coordinate filters weren't applied
        args, kwargs = mock_fetch.call_args
        filter_criteria = kwargs.get("filter_criteria", {})
        assert "lat_lon.latitude" not in filter_criteria
        assert "lat_lon.longitude" not in filter_criteria

    @patch("nmdc_mcp.tools.fetch_nmdc_biosample_records_paged")
    def test_get_random_biosample_subset_with_filters(self, mock_fetch):
        mock_fetch.return_value = [{"id": "sample1", "ecosystem_type": "Soil"}]

        get_random_biosample_subset(
            sample_count=1, filter_criteria={"ecosystem_type": "Soil"}
        )

        # Check that filters were merged correctly
        args, kwargs = mock_fetch.call_args
        filter_criteria = kwargs.get("filter_criteria", {})
        assert "ecosystem_type" in filter_criteria
        assert filter_criteria["ecosystem_type"] == "Soil"

    @patch("nmdc_mcp.tools.fetch_nmdc_biosample_records_paged")
    def test_get_random_biosample_subset_api_error(self, mock_fetch):
        mock_fetch.side_effect = Exception("API Error")

        result = get_random_biosample_subset(sample_count=1)

        assert len(result) == 1
        assert "error" in result[0]
        assert "Failed to fetch random samples" in result[0]["error"]


class TestGetRandomCollectionSubset:
    """Test the get_random_collection_subset function."""

    @patch("nmdc_mcp.tools.fetch_nmdc_collection_records_paged")
    @patch("nmdc_mcp.tools.random.randint")
    @patch("nmdc_mcp.tools.random.sample")
    def test_get_random_collection_subset_basic(
        self, mock_sample, mock_randint, mock_fetch
    ):
        # Setup mocks
        mock_randint.return_value = 5
        mock_records = [{"id": f"study{i}", "name": f"Study {i}"} for i in range(10)]
        mock_fetch.return_value = mock_records
        mock_sample.return_value = mock_records[:3]

        # Call function
        result = get_random_collection_subset(collection="study_set", sample_count=3)

        # Assertions
        assert len(result) == 3
        mock_fetch.assert_called_once()
        args, kwargs = mock_fetch.call_args
        assert kwargs["collection"] == "study_set"

    @patch("nmdc_mcp.tools.fetch_nmdc_collection_records_paged")
    def test_get_random_collection_subset_empty_pool(self, mock_fetch):
        mock_fetch.return_value = []

        result = get_random_collection_subset(collection="study_set", sample_count=5)

        assert len(result) == 1
        assert "error" in result[0]
        assert "No records found in study_set" in result[0]["error"]

    @patch("nmdc_mcp.tools.fetch_nmdc_collection_records_paged")
    def test_get_random_collection_subset_with_projection(self, mock_fetch):
        mock_fetch.return_value = [{"id": "study1", "type": "metagenome"}]

        get_random_collection_subset(
            collection="omics_processing_set", sample_count=1, projection=["id", "type"]
        )

        # Check that projection was passed correctly
        args, kwargs = mock_fetch.call_args
        assert "projection" in kwargs
        assert kwargs["projection"] == ["id", "type"]

    @patch("nmdc_mcp.tools.fetch_nmdc_collection_records_paged")
    def test_get_random_collection_subset_with_filters(self, mock_fetch):
        mock_fetch.return_value = [{"id": "study1", "ecosystem_type": "Soil"}]

        get_random_collection_subset(
            collection="biosample_set",
            sample_count=1,
            filter_criteria={"ecosystem_type": "Soil"},
        )

        # Check that filters were passed correctly
        args, kwargs = mock_fetch.call_args
        assert "filter_criteria" in kwargs
        assert kwargs["filter_criteria"]["ecosystem_type"] == "Soil"

    @patch("nmdc_mcp.tools.fetch_nmdc_collection_records_paged")
    def test_get_random_collection_subset_api_error(self, mock_fetch):
        mock_fetch.side_effect = Exception("API Error")

        result = get_random_collection_subset(collection="study_set", sample_count=1)

        assert len(result) == 1
        assert "error" in result[0]
        assert "Failed to fetch samples from study_set" in result[0]["error"]

    @patch("nmdc_mcp.tools.fetch_nmdc_collection_records_paged")
    def test_get_random_collection_subset_defaults(self, mock_fetch):
        mock_fetch.return_value = [{"id": "sample1", "name": "test"}]

        get_random_collection_subset()

        # Check defaults were applied
        args, kwargs = mock_fetch.call_args
        assert kwargs["collection"] == "biosample_set"
        assert kwargs["projection"] == ["id", "name"]
