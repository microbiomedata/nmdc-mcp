# Debug Logging Implementation Summary

## Problem Statement

The `local/claude-demo-bacterial-pfam-search.txt` demo was exhibiting non-deterministic behavior:
- Sometimes it would find data objects and fetch individual data objects
- Other times it would report "no relevant data objects found"
- The only change made between runs was adding a `timeout 120s` to prevent hanging
- The user suspected the tool should be able to work with inlined data objects from the PFAM functional annotation search

## Root Cause Investigation

The inconsistent behavior suggested one of three potential issues:
1. **API response variations** - The NMDC API returning different data structures between calls
2. **Claude's non-deterministic decision making** - The LLM making different choices about data processing
3. **Bug in data parsing logic** - Our code missing certain data extraction paths

## Solution Implemented

### Debug Logging Addition

Added comprehensive debug logging to the `find_data_objects_by_pfam_domains` function in `src/nmdc_mcp/tools.py` (lines ~1404-1441) to trace:

```python
# Debug: Log what we're processing
logger.debug(f"Processing biosample {biosample_id}")
logger.debug(f"Biosample keys: {list(biosample.keys())}")

omics_processing = biosample.get("omics_processing", [])
logger.debug(f"Found {len(omics_processing)} omics_processing entries")

for i, omics in enumerate(omics_processing):
    logger.debug(f"Omics {i} keys: {list(omics.keys())}")
    
    # Direct data objects in omics processing
    if "omics_data" in omics:
        direct_data = omics.get("omics_data", [])
        logger.debug(f"Found {len(direct_data)} direct omics_data objects")
        
    # Check for results array structure
    if "results" in omics:
        results_array = omics.get("results", [])
        logger.debug(f"Found {len(results_array)} results entries")
        for result in results_array:
            if "omics_processing" in result:
                for nested_omics in result["omics_processing"]:
                    if "omics_data" in nested_omics:
                        nested_data = nested_omics.get("omics_data", [])
                        logger.debug(f"Found {len(nested_data)} nested omics_data objects")
    
    logger.debug(f"Total data_objects for omics {i}: {len(data_objects)}")
```

### Key Diagnostic Points

The debug logging captures:

1. **Biosample Structure Analysis**
   - Which biosample IDs are being processed
   - What keys are available in each biosample record
   - How many omics_processing entries exist per biosample

2. **Data Object Discovery Paths**
   - Direct `omics_data` objects in omics processing
   - Nested `omics_data` objects in results arrays
   - Total count of data objects found per omics processing entry

3. **Data Extraction Logic**
   - Whether data objects exist in expected locations
   - Different nested data organization patterns
   - Empty omics_processing arrays vs populated ones

## Implementation Details

### Initial Approach (Problematic)
- Used `print()` statements for debug output
- Would contaminate Claude agent responses with debug text
- Caused performance degradation

### Final Solution
- Replaced all `print()` statements with `logger.debug()` calls
- Added proper logging import: `logger = logging.getLogger(__name__)`
- Debug output only appears when logging level explicitly configured
- No performance impact on normal MCP tool usage
- Clean separation of diagnostic info from user-facing responses

### Code Quality
- Fixed all linting issues (E501 line length, E402 import order)
- Passed type checking with mypy
- Maintained code formatting standards

## Expected Diagnostic Outcomes

This debug logging should reveal:

1. **API Consistency**: Whether the NMDC API returns consistent data structures across calls
2. **Data Availability**: Whether biosample records contain the expected omics_processing data
3. **Parsing Logic**: Whether our code correctly finds data objects in all possible nested locations
4. **Empty Results**: Whether "no data objects" means truly empty responses or missed parsing paths

## Usage

To enable debug logging for diagnosis:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

To run the demo:
```bash
make local/claude-demo-bacterial-pfam-search.txt
```

## Files Modified

- `src/nmdc_mcp/tools.py`: Added debug logging to `find_data_objects_by_pfam_domains` function
- Fixed import order and line length issues for code quality

## Next Steps

1. Run the demo again to see if non-deterministic behavior persists
2. If issues continue, enable debug logging to analyze the diagnostic output
3. Based on debug findings, implement targeted fixes for data extraction logic
4. Once root cause identified, remove or minimize debug logging for production use