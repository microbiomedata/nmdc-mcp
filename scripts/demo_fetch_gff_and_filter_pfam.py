#!/usr/bin/env python3
"""
Demonstrate the complete data object workflow:
1. Fetch data object metadata with download URL from runtime API
2. Download content from the resolved URL
3. Filter content for specific PFAM domains

This script shows the same workflow as the Makefile targets but in Python.
"""

import json
import requests
import sys
from typing import List, Optional


def fetch_data_object_metadata(data_object_id: str) -> dict:
    """Fetch data object metadata from the runtime API."""
    url = f"https://api.microbiomedata.org/data_objects/{data_object_id}"
    print(f"🔍 Fetching metadata for data object: {data_object_id}")

    response = requests.get(url, headers={"Accept": "application/json"})
    response.raise_for_status()

    metadata = response.json()
    print(f"✅ Got metadata with download URL: {metadata.get('url', 'No URL found')}")
    return metadata


def download_content_sample(download_url: str, max_bytes: int = 1024 * 1024) -> str:
    """Download a sample of content from the URL (limited to max_bytes)."""
    print(f"📥 Downloading content sample from: {download_url}")
    print(f"   Limiting to first {max_bytes:,} bytes")

    headers = {"Range": f"bytes=0-{max_bytes-1}"}
    response = requests.get(download_url, headers=headers, stream=True)
    response.raise_for_status()

    content = response.text
    print(f"✅ Downloaded {len(content):,} characters")
    return content


def filter_pfam_domains(content: str, pfam_domains: List[str]) -> List[str]:
    """Filter content lines that contain any of the specified PFAM domains."""
    print(f"🔬 Filtering for PFAM domains: {', '.join(pfam_domains)}")

    matching_lines = []
    total_lines = 0

    for line in content.splitlines():
        total_lines += 1
        # Check if line contains any of the PFAM domains (case insensitive)
        for domain in pfam_domains:
            if (
                f"pfam={domain.lower()}" in line.lower()
                or f"pfam={domain.upper()}" in line.lower()
            ):
                matching_lines.append(line)
                break

    print(
        f"✅ Found {len(matching_lines)} matching lines out of {total_lines} total lines"
    )
    return matching_lines


def main():
    """Run the complete workflow demonstration."""
    # Configuration
    data_object_id = "nmdc%3Adobj-11-wcxahg62"  # URL-encoded nmdc:dobj-11-wcxahg62
    pfam_domains = ["PF13243", "PF02401"]  # Updated to match the Makefile
    max_download_bytes = 1024 * 1024  # 1MB sample

    try:
        # Step 1: Fetch metadata
        metadata = fetch_data_object_metadata(data_object_id)

        # Step 2: Download content sample
        download_url = metadata.get("url")
        if not download_url:
            print("❌ No download URL found in metadata")
            return 1

        content = download_content_sample(download_url, max_download_bytes)

        # Step 3: Filter for PFAM domains
        matching_lines = filter_pfam_domains(content, pfam_domains)

        # Output results
        print(f"\n📋 Results Summary:")
        print(f"   Data Object ID: {data_object_id}")
        print(f"   Download URL: {download_url}")
        print(f"   Content sample size: {len(content):,} characters")
        print(f"   PFAM domains searched: {', '.join(pfam_domains)}")
        print(f"   Matching lines found: {len(matching_lines)}")

        if matching_lines:
            print(f"\n🔍 Sample matching lines:")
            for i, line in enumerate(matching_lines[:3]):  # Show first 3 matches
                print(f"   {i+1}: {line[:100]}{'...' if len(line) > 100 else ''}")
            if len(matching_lines) > 3:
                print(f"   ... and {len(matching_lines) - 3} more")

        # Create output object for JSON serialization
        result = {
            "data_object_id": data_object_id,
            "download_url": download_url,
            "content_sample_size": len(content),
            "pfam_domains_searched": pfam_domains,
            "matching_lines_count": len(matching_lines),
            "sample_matches": matching_lines[:5],  # Include first 5 matches in output
        }

        # Output JSON result
        print(f"\n📄 JSON Output:")
        print(json.dumps(result, indent=2))

        return 0

    except requests.RequestException as e:
        print(f"❌ Network error: {e}")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
