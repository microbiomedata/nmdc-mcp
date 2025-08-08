#!/usr/bin/env python3
"""
Test script for the new fetch_and_filter_gff_by_pfam_domains MCP tool.

This script exercises the consolidated MCP tool that:
1. Fetches data object metadata from runtime API
2. Downloads GFF content with byte limiting
3. Filters for specified PFAM domains

This will eventually replace scripts/demo_fetch_gff_and_filter_pfam.py.
"""

import json
import sys
from pathlib import Path

# Add the src directory to Python path so we can import the tools
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from nmdc_mcp.tools import fetch_and_filter_gff_by_pfam_domains


def main():
    """Test the new consolidated MCP tool."""
    print("🧪 Testing fetch_and_filter_gff_by_pfam_domains MCP tool")

    # Test configuration - same as the demo script
    data_object_id = "nmdc:dobj-11-wcxahg62"
    pfam_domains = ["PF13243", "PF02401"]  # Match the Makefile targets
    max_rows = 100  # Limit for testing
    sample_bytes = 1048576  # 1MB sample

    print(f"📋 Test Parameters:")
    print(f"   Data Object ID: {data_object_id}")
    print(f"   PFAM Domains: {', '.join(pfam_domains)}")
    print(f"   Max Rows: {max_rows}")
    print(f"   Sample Bytes: {sample_bytes:,}")
    print()

    try:
        # Call the MCP tool
        result = fetch_and_filter_gff_by_pfam_domains(
            data_object_id=data_object_id,
            pfam_domain_ids=pfam_domains,
            max_rows=max_rows,
            sample_bytes=sample_bytes,
        )

        # Check for errors
        if "error" in result:
            print(f"❌ Tool returned error: {result['error']}")
            return 1

        # Display summary information
        summary = result.get("summary", {})
        file_info = result.get("file_info", {})
        matching_annotations = result.get("matching_annotations", [])

        print(f"📊 Results Summary:")
        print(
            f"   Total matching annotations: {summary.get('total_matching_annotations', 0)}"
        )
        print(f"   File size processed: {summary.get('file_size_bytes', 0):,} bytes")
        print(f"   File was truncated: {file_info.get('was_truncated', False)}")
        print(f"   Total rows processed: {file_info.get('total_rows_processed', 0)}")
        print()

        # Show sample annotations
        if matching_annotations:
            print(
                f"🔍 Sample Matching Annotations ({min(3, len(matching_annotations))} of {len(matching_annotations)}):"
            )
            for i, annotation in enumerate(matching_annotations[:3]):
                if "raw_line" in annotation:
                    line = annotation["raw_line"]
                    # Truncate long lines for display
                    display_line = line[:100] + "..." if len(line) > 100 else line
                    print(f"   {i+1}: {display_line}")
                else:
                    print(f"   {i+1}: {annotation}")

            if len(matching_annotations) > 3:
                print(f"   ... and {len(matching_annotations) - 3} more annotations")
        else:
            print("🔍 No matching annotations found")

        print()

        # Output complete result as JSON
        print("📄 Complete JSON Result:")
        print(json.dumps(result, indent=2))

        return 0

    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
