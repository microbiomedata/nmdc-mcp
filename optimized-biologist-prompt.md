# Optimized Biologist Prompt for PFAM Domain Analysis

## Recommended Prompt

```
I need to find 1 sample with both PF04183 and PF06276 domains and see where these genes are located in the genome.
```

## What This Prompt Accomplishes

This simple, natural prompt triggers an optimized 2-step workflow:

### Step 1: Find Sample with Domains
- **Tool**: `get_samples_by_annotation`
- **Parameters**: 
  - `gene_function_ids: ["PFAM:PF04183", "PFAM:PF06276"]`
  - `max_records: 1`
- **Result**: Complete biosample record with all data objects (including GFF files)

### Step 2: Analyze Genomic Locations
- **Tool**: `fetch_and_filter_gff_by_pfam_domains`
- **Parameters**:
  - `data_object_id`: GFF file ID from Step 1 results
  - `pfam_domain_ids: ["PF04183", "PF06276"]`
- **Result**: Genomic coordinates and gene context for the domains

## Key Optimizations

✅ **No redundant API calls** - avoids unnecessary `get_entity_by_id` lookups
✅ **Correct parameter usage** - uses `max_records` instead of `limit`
✅ **Proper format handling** - uses correct PFAM format without second-guessing
✅ **Exact quantity control** - returns exactly 1 sample as requested

## Domain Information

- **PF04183**: Sigma-54 interaction domain (transcriptional regulation)
- **PF06276**: Response regulator receiver domain (two-component systems)

These domains often work together in bacterial two-component regulatory systems.

## Expected Workflow

1. User enters the simple prompt
2. System finds 1 biosample containing both domains
3. System identifies GFF annotation files in the results
4. System downloads and filters the GFF file to show genomic coordinates
5. User sees the actual gene locations and genomic context

**Total API calls: 2** (optimal efficiency)