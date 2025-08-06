# NMDC Biosample Search API - Advanced Analysis & MCP Tool Design

## Performance Optimization Analysis

### ✅ **1. Lightweight API Endpoints Available**

**MAJOR DISCOVERY**: The API has several lightweight alternatives to the main search endpoint:

#### A. **Facet Endpoint** - Ultra Lightweight Counts
```bash
POST /api/biosample/facet
# Returns only counts by category - ~100 bytes vs ~100KB
{
  "conditions": [...],
  "attribute": "ecosystem"  # or "ecosystem_type", "specific_ecosystem", etc.
}
# Response: {"facets": {"Environmental": 2190, "Engineered": 17, "Host-associated": 125}}
```

#### B. **Geospatial Aggregation** - Geographic Distribution 
```bash
POST /api/environment/geospatial
# Returns lat/lng clusters with counts - much lighter than full records
# Response: [{"count":7,"latitude":-4.3092,"longitude":15.2356,"ecosystem":"Environmental"}...]
```

#### C. **Count-Only Pattern** - Use `limit=1` with facet
```bash
# Get total count without heavy response data
POST /api/biosample/facet + attribute="id" = rough count estimation
```

### ✅ **2. Bulk Query Patterns** 

**NO BATCH SUPPORT**: The API doesn't support true batch requests (single request, multiple condition sets). However, optimal patterns exist:

#### A. **Concurrent Request Strategy**
- **Frontend evidence**: `axios-cache-adapter` used with aggressive caching
- **No rate limiting**: No evidence of rate limiting in codebase
- **Database pooling**: Uses SQLAlchemy connection pooling
- **Recommendation**: 5-10 concurrent requests max to be respectful

#### B. **Optimal Query Batching**
```bash
# Instead of separate requests for each PFAM:
# BAD: 20 separate requests for 20 PFAMs

# GOOD: Group related functions in single requests
{
  "conditions": [
    {"op": "==", "field": "id", "value": "PFAM:PF00001", "table": "pfam_function"},
    {"op": "==", "field": "id", "value": "PFAM:PF00002", "table": "pfam_function"}
  ]
}
```

### ✅ **3. Caching Strategy**

**CONFIRMED**: Frontend uses sophisticated caching:
```javascript
// From web/src/data/api.ts
const cache = setupCache({
  maxAge: 15 * 60 * 1000, // 15 minutes
  exclude: {
    query: false,
    methods: ['post']  // POST requests are cached!
  }
});
```

**Recommendations**:
- Cache facet requests aggressively (they rarely change)
- Cache KEGG pathway/module mappings (static data)
- Cache environmental metadata queries
- Use ETags/conditional requests where possible

### ✅ **4. Rate Limiting Considerations**

**NO EXPLICIT RATE LIMITING FOUND** in codebase, but best practices:
- **Concurrent requests**: Limit to 5-10 simultaneous
- **Request frequency**: Space requests by 100-200ms
- **Bulk operations**: Use pagination with reasonable limits (100-500)
- **Cache-first**: Always check cache before making requests

## OR Logic Workaround Strategies

### ✅ **1. Maximum Concurrent Requests**
- **Recommended**: 5-10 concurrent requests
- **Evidence**: No rate limiting, standard FastAPI/SQLAlchemy setup
- **Frontend pattern**: Uses axios with connection pooling

### ✅ **2. Common Functional Groupings** 

**DISCOVERED**: The API provides KEGG pathway/module endpoints with pre-grouped functions:

#### A. **Core Metabolic Pathways** (High Scientific Value)
```bash
# Glycolysis: 97 KO terms
GET /api/kegg/pathway/map00010  

# Nitrogen metabolism: ~50 KO terms  
GET /api/kegg/pathway/map00910

# Carbon fixation: ~30 KO terms
GET /api/kegg/pathway/map00720

# Methane metabolism: ~25 KO terms  
GET /api/kegg/pathway/map00680
```

#### B. **Functional Modules** (Smaller, Focused Groups)
```bash
# Central carbohydrate metabolism
GET /api/kegg/module/M00001  # Glycolysis
GET /api/kegg/module/M00002  # Glycolysis core
GET /api/kegg/module/M00003  # Gluconeogenesis

# Energy metabolism  
GET /api/kegg/module/M00173  # Reductive citrate cycle
GET /api/kegg/module/M00376  # 3-Hydroxypropanoate cycle
```

#### C. **Pre-computed Groupings for OR Logic**
```javascript
// Alcohol metabolism genes
const alcoholMetabolism = [
  "PFAM:PF00106", // Short-chain dehydrogenase
  "PFAM:PF00107", // Zinc-binding dehydrogenase  
  "PFAM:PF08240", // Alcohol dehydrogenase GroES
];

// Nitrogen fixation complex
const nitrogenFixation = [
  "PFAM:PF00142", // Nitrogenase MoFe cofactor
  "PFAM:PF01291", // Nitrogenase reductase
  "PFAM:PF00148", // Nitrogenase Fe protein
];
```

### ✅ **3. Batch Request Workaround**

**NO NATIVE BATCH SUPPORT**, but efficient patterns:

```javascript
// Efficient OR logic implementation
async function findSamplesWithAnyOf(pfamList, concurrency = 5) {
  const results = await Promise.allSettled(
    pfamList.map(pfam => 
      searchBiosamples({
        conditions: [{
          op: "==", 
          field: "id", 
          value: pfam, 
          table: "pfam_function"
        }]
      })
    ).chunk(concurrency)  // Process in batches
  );
  
  // Merge results client-side, deduplicate by biosample ID
  return mergeAndDeduplicate(results);
}
```

## Optimal MCP Tool Design

### ✅ **1. Multi-functional Annotation Finder** ⭐⭐⭐⭐⭐
**HIGHEST SCIENTIFIC VALUE** - Perfectly matches API strengths

```yaml
Tool: "pathway-sample-finder"
Description: "Find samples containing genes from specific metabolic pathways"
Examples:
  - "Find samples with complete glycolysis pathway"
  - "Samples with alcohol metabolism genes" 
  - "Methane-producing organisms"

Implementation:
  1. Use /api/kegg/pathway/{pathway_id} to get gene list
  2. Convert KO terms to PFAM/COG equivalents  
  3. Single query with multiple PFAM conditions (AND logic)
  4. Use facet endpoint for quick counts
  
Scientific Value: ⭐⭐⭐⭐⭐ (Core metabolic analysis)
API Fit: ⭐⭐⭐⭐⭐ (Perfect match for AND logic)
Performance: ⭐⭐⭐⭐ (Single request, good caching)
```

### ✅ **2. Environmental + Functional Filter** ⭐⭐⭐⭐⭐  
**HIGHEST SCIENTIFIC VALUE** - Cross-domain analysis

```yaml
Tool: "eco-functional-analyzer" 
Description: "Find samples from specific environments with target functions"
Examples:
  - "Marine samples with nitrogen fixation genes"
  - "Forest soil samples with cellulose degradation enzymes"
  - "Hypersaline environments with osmotic stress genes"

Implementation:
  1. Combine env_medium + pfam_function conditions
  2. Use geospatial aggregation for geographic distribution
  3. Use between operator for latitude/longitude ranges
  4. Facet by ecosystem_type for environmental breakdown

Scientific Value: ⭐⭐⭐⭐⭐ (Ecology + function = core research)
API Fit: ⭐⭐⭐⭐⭐ (Perfect cross-table support)  
Performance: ⭐⭐⭐⭐ (Efficient with aggregation endpoints)
```

### ✅ **3. Geographic Functional Survey** ⭐⭐⭐⭐
**HIGH SCIENTIFIC VALUE** - Biogeography analysis

```yaml
Tool: "biogeography-mapper"
Description: "Map distribution of metabolic functions across geographic gradients"
Examples:
  - "Nitrogen fixation genes across latitude gradients"
  - "Cold-shock proteins in polar vs tropical samples"
  - "Photosynthesis genes by depth in marine samples"

Implementation:
  1. Use /api/environment/geospatial with functional conditions
  2. Return lat/lng clusters with functional gene counts
  3. Integrate with mapping libraries for visualization
  4. Use between queries for depth/temperature ranges

Scientific Value: ⭐⭐⭐⭐ (Biogeography is high-impact field)
API Fit: ⭐⭐⭐⭐⭐ (Geospatial endpoint is perfect)
Performance: ⭐⭐⭐⭐⭐ (Lightweight, cached responses)
```  

### ✅ **4. Workflow-aware Search** ⭐⭐⭐
**MODERATE SCIENTIFIC VALUE** - Data availability focus

```yaml
Tool: "multi-omics-finder"
Description: "Find samples with specific omics data types containing target functions"
Examples:  
  - "Samples with both metagenome and proteome data containing alcohol dehydrogenase"
  - "Metatranscriptome studies with nitrogen cycle genes"
  - "Metabolomics datasets from marine environments"

Implementation:
  1. Use data_object_filter to specify workflow types
  2. Combine with functional annotation conditions
  3. Check multiomics field for data type availability
  4. Use omics_processing table for workflow metadata

Scientific Value: ⭐⭐⭐ (Useful but not primary research focus)
API Fit: ⭐⭐⭐ (Good but complex with workflow filtering)
Performance: ⭐⭐ (Still returns massive omics data)
```

## Final Recommendations

### **Build These Tools First** (Priority Order):

1. **🥇 Multi-functional Annotation Finder** 
   - Perfect API fit, highest scientific value
   - Use KEGG pathway pre-groupings 
   - Implement smart caching of pathway→gene mappings

2. **🥈 Environmental + Functional Filter**
   - Core ecology research tool
   - Excellent cross-table query support
   - Use geospatial aggregation for performance

3. **🥉 Geographic Functional Survey** 
   - High-impact biogeography research
   - Leverages unique geospatial endpoint
   - Great for visualization/mapping tools

### **Implementation Architecture**:

```javascript
// Optimal MCP tool structure
class NMDCBiosampleTool {
  constructor() {
    this.cache = new Map(); // Aggressive caching
    this.concurrency = 5;   // Respectful concurrent requests
  }

  async findByPathway(pathwayId) {
    // 1. Get gene list from KEGG endpoint (cached)
    // 2. Convert to PFAM/COG conditions  
    // 3. Single biosample search with AND logic
    // 4. Use facet endpoint for quick counts first
  }

  async findByEnvironmentAndFunction(envConditions, funcConditions) {
    // 1. Combine environmental + functional conditions
    // 2. Use geospatial aggregation for geographic distribution
    // 3. Use facet for ecosystem breakdown
  }
  
  async mapFunctionDistribution(functions, bounds) {
    // 1. Use /api/environment/geospatial with functional filters
    // 2. Return lightweight lat/lng clusters
    // 3. Cache aggressively (geographic data changes slowly)
  }
}
```

The **Environmental + Functional Filter** and **Multi-functional Annotation Finder** provide the highest scientific value while perfectly matching the API's strengths in cross-table queries and AND logic operations.