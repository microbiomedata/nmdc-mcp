# NMDC Biosample Search API - Complete Research Findings

## Executive Summary

✅ **CONFIRMED**: The NMDC Biosample Search API supports complex multi-condition queries with AND logic, making it powerful for sophisticated biological searches.

❌ **LIMITATION**: No way to get lightweight responses - projection parameter is non-functional and all queries return massive omics workflow data.

## Research Questions Answered

### ✅ 1. **Multi-PFAM Query Logic (AND vs OR)**
**CONFIRMED: Multiple conditions use AND logic**

- **Test**: Queried for biosamples with BOTH `PFAM:PF00005` (ABC transporter) AND `PFAM:PF00072` (response regulator)
- **Result**: 5,734 biosamples containing BOTH PFAMs
- **Answer**: Multi-condition queries work perfectly with implicit AND logic between conditions

### ✅ 2. **data_object_filter Parameter**  
**CONFIRMED: Controls workflow data selection for downloads, NOT response size**

From codebase analysis (`nmdc_server/data_object_filters.py`):
```python
class DataObjectFilter(BaseModel):
    workflow: Optional[WorkflowActivityTypeEnum] = None
    file_type: Optional[str] = None
```

- **Format**: `[{"workflow": "nmdc:WorkflowType", "file_type": "FileType"}]`
- **Available workflows**: `nmdc:RawData`, `nmdc:MetagenomeAssembly`, `nmdc:ReadQcAnalysis`, `nmdc:MetaproteomicsAnalysis`, etc.
- **Function**: Marks data objects as "selected" for bulk download purposes
- **Does NOT**: Reduce response payload size or eliminate omics data from response
- **Answer**: Used for download filtering, not response control

### ✅ 3. **Available Operators**
**CONFIRMED: Rich but limited operator set**

From API error messages and codebase analysis (`nmdc_server/query.py`):

**Simple Operators**: `==`, `>`, `>=`, `<`, `<=`, `!=`, `like`
**Range Operator**: `between` (for numeric ranges like latitude, longitude)  
**Special Operators**: 
- `tree` (for `gold_tree` field only)
- `has` (for `multiomics` field only)

**NOT SUPPORTED**: `IN`, `NOT IN`, set operations

**Answer**: Comprehensive operators for most use cases, but no set operations

### ✅ 4. **Available Tables and Fields**
**CONFIRMED: Extensive table support**

From codebase analysis (`nmdc_server/table.py`):

**Core Biosample Tables:**
- `biosample` - id, name, description, latitude, longitude, collection_date, etc.
- `study` - id, name, title, description, part_of, etc.
- `omics_processing` - id, name, omics_type, instrument_name, etc.

**Environmental Metadata Tables:**
- `env_broad_scale` - ENVO terms for broad environmental context
- `env_local_scale` - ENVO terms for local environmental context  
- `env_medium` - ENVO terms for environmental medium

**Functional Annotation Tables:**
- `pfam_function` - Pfam domain annotations (id, name, description)
- `kegg_function` - KEGG pathway/enzyme annotations
- `cog_function` - COG functional annotations
- `go_function` - Gene Ontology annotations
- `gene_function` - General gene function annotations

**Workflow Tables:**
- `reads_qc`, `metagenome_assembly`, `metagenome_annotation`
- `metatranscriptome_assembly`, `metatranscriptome_annotation`
- `metaproteomic_analysis`, `mags_analysis`, `nom_analysis`
- `read_based_analysis`, `metabolomics_analysis`

**Answer**: Comprehensive schema supporting all major NMDC data types

### ❌ 5. **Projection Parameter**
**CONFIRMED: Completely non-functional**

- **Test**: Used `"projection": ["id", "name"]` in multiple queries
- **Result**: Always returns full biosample objects with 30+ fields
- **Conclusion**: Projection parameter is ignored by the server
- **Answer**: No way to get lightweight responses - always receive complete data

### ❌ 6. **Response Size Control**
**CONFIRMED: No effective control mechanisms**

- Cannot eliminate omics workflow data from responses
- Each biosample includes complete `omics_processing` arrays with:
  - Raw data file references
  - All workflow outputs (sometimes 10+ data objects per workflow)
  - Complete metadata for each workflow step
- Only control: `limit` parameter to restrict number of biosamples
- **Answer**: No lightweight mode - responses are always massive

## Working Query Examples

### Multi-PFAM Query (AND Logic)
```bash
curl -X POST "https://data.microbiomedata.org/api/biosample/search?limit=5" \
  -H "Content-Type: application/json" \
  -d '{
    "conditions": [
      {
        "op": "==",
        "field": "id",
        "value": "PFAM:PF00005",
        "table": "pfam_function"
      },
      {
        "op": "==",
        "field": "id",
        "value": "PFAM:PF00072", 
        "table": "pfam_function"
      }
    ]
  }'
```

### Geographic Range + Environmental Filter
```bash
curl -X POST "https://data.microbiomedata.org/api/biosample/search?limit=5" \
  -H "Content-Type: application/json" \
  -d '{
    "conditions": [
      {
        "op": "between",
        "field": "latitude",
        "value": [40, 45],
        "table": "biosample"
      },
      {
        "op": "==",
        "field": "id", 
        "value": "ENVO:00002261",
        "table": "env_medium"
      }
    ]
  }'
```

### Complex Cross-Table Query
```bash
curl -X POST "https://data.microbiomedata.org/api/biosample/search?limit=1" \
  -H "Content-Type: application/json" \
  -d '{
    "conditions": [
      {
        "op": "==",
        "field": "id",
        "value": "ENVO:00002261",
        "table": "env_medium"
      },
      {
        "op": "==", 
        "field": "id",
        "value": "PFAM:PF00005",
        "table": "pfam_function"
      },
      {
        "op": "between",
        "field": "latitude",
        "value": [40, 45],
        "table": "biosample"
      }
    ]
  }'
```

### Pattern Matching with LIKE
```bash
curl -X POST "https://data.microbiomedata.org/api/biosample/search?limit=5" \
  -H "Content-Type: application/json" \
  -d '{
    "conditions": [
      {
        "op": "like",
        "field": "name", 
        "value": "%forest%",
        "table": "biosample"
      }
    ]
  }'
```

## Architecture Insights (From Codebase Analysis)

### Query Processing Flow
1. **API Endpoint**: `/api/biosample/search` in `nmdc_server/api.py:217-276`
2. **Query Schema**: `BiosampleSearchQuery` in `nmdc_server/query.py:1042`
3. **CRUD Operations**: `search_biosample()` in `nmdc_server/crud.py`
4. **Data Object Selection**: Applied via `insert_selected()` function using `data_object_filter`

### Key Code Patterns
```python
# Multiple conditions are combined with AND logic
conditions = [condition1, condition2, condition3]  # All must be true

# Data object filter structure  
data_object_filter = [
    {"workflow": "nmdc:MetagenomeAssembly", "file_type": "Assembly Contigs"}
]

# Range condition format
range_condition = {
    "op": "between", 
    "field": "latitude",
    "value": [min_value, max_value],
    "table": "biosample"
}
```

## Limitations for MCP Tools

### Major Limitations
1. **No lightweight responses** - Always receive massive omics workflow data
2. **No OR logic** - Cannot express "PFAM A OR PFAM B" in single condition
3. **No set operations** - Cannot use IN operator for multiple values
4. **No exclusion** - Cannot directly exclude results (no NOT operator)

### Performance Considerations
- Large responses (often >100KB per biosample due to omics data)
- Network-intensive for bulk operations
- Client-side filtering required for complex boolean logic

### Workarounds
1. **OR Logic**: Make separate queries and merge results client-side
2. **Set Operations**: Use multiple `==` conditions with different values
3. **Exclusion**: Query inclusively, then filter results client-side
4. **Lightweight Data**: Extract only needed fields from large responses

## Recommendations for MCP Tools

### ✅ Optimal Use Cases
1. **Multi-functional annotation queries** - Works perfectly with AND logic
2. **Geographic + environmental filtering** - Excellent support
3. **Cross-table complex searches** - Fully supported
4. **Range-based queries** - Great for numeric fields

### ⚠️ Suboptimal Use Cases  
1. **High-frequency lightweight queries** - Responses too large
2. **OR-heavy boolean logic** - Requires multiple API calls
3. **Real-time applications** - Response size may cause latency

### Implementation Strategy
1. **Cache aggressively** - Responses are expensive to fetch
2. **Use pagination** - Limit results with `?limit=N`
3. **Post-process data** - Extract minimal needed information
4. **Batch related queries** - Combine multiple conditions when possible

## Use Case Assessment ✅

### ✅ "Samples with both alcohol dehydrogenase AND acetaldehyde dehydrogenase"
**Status**: FULLY SUPPORTED
- Use multiple PFAM conditions with AND logic
- Example: PF00106 (short-chain dehydrogenase) + PF00107 (zinc dehydrogenase)

### ✅ "Marine samples with nitrogen fixation genes from studies published after 2020"
**Status**: FULLY SUPPORTED  
- Combine `env_medium` + `pfam_function` + `study` conditions
- Use date range queries on study metadata

### ⚠️ "Soil samples with specific PFAM domains but excluding certain COG functions"  
**Status**: PARTIALLY SUPPORTED
- Inclusion queries work perfectly (soil + PFAM conditions)
- Exclusion requires client-side filtering (no direct NOT support)
- Workaround: Query positive conditions, filter results

## Conclusion

The NMDC Biosample Search API is **highly capable** for complex biological queries with some significant limitations:

**Strengths:**
- Powerful AND-logic multi-condition queries
- Comprehensive schema coverage (environmental, functional, geographic)
- Rich operator support including ranges and pattern matching
- Cross-table joins work seamlessly

**Critical Limitations:**
- No lightweight response mode (major performance issue)
- No direct OR/NOT logic support
- No set operations (IN/NOT IN)

**Overall Assessment**: Excellent for sophisticated biological research queries, but requires careful client-side optimization due to response size issues.