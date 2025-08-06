#!/usr/bin/env python3
"""
Script to test the new get_data_objects_by_pfam_domains tool and save output to JSON.
"""

import json
import sys
import os
from io import StringIO

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def main():
    # Capture stdout to suppress debug output from the API module
    old_stdout = sys.stdout
    sys.stdout = StringIO()
    
    try:
        from nmdc_mcp.tools import get_data_objects_by_pfam_domains
        
        # Test with PF00005 (ABC transporter) and PF00072 (response regulator)
        result = get_data_objects_by_pfam_domains(['PF04183', 'PF06276'], biosample_limit=100)
    finally:
        # Restore stdout
        sys.stdout = old_stdout
    
    # Print only the JSON to stdout
    print(json.dumps(result, indent=2, default=str))

if __name__ == "__main__":
    main()