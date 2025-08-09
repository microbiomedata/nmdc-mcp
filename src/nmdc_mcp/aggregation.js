// Aggregation for annotation -> dobj
db.getCollection("functional_annotation_agg").aggregate([
  // Match documents with gene_function_id in the list
  {
    $match: {
      "gene_function_id": { $in: ["PFAM:PF06276", "PFAM:PF04183"] }
    }
  },
  // Group by was_generated_by and count occurrences
  {
    $group: {
      _id: "$was_generated_by",
      count: { $sum: 1 }
    }
  },
  // Only keep groups with more than one document (common was_generated_by)
  {
    $match: {
      count: { $gt: 1 }
    }
  },
  // Project to return just the was_generated_by ID
  {
    $project: {
      was_generated_by: "$_id",
      _id: 0
    }
  },
    // Lookup in workflow_execution_set collection
  {
    $lookup: {
      from: "workflow_execution_set",
      localField: "was_generated_by",
      foreignField: "id", // assuming the join field is _id in workflow_execution_set
      as: "workflow_execution"
    }
  },
  // Unwind the lookup result (assuming one-to-one relationship)
  {
    $unwind: "$workflow_execution"
  },
    // Lookup data objects using the has_output IDs
  {
    $lookup: {
      from: "data_object_set",
      localField: "workflow_execution.has_output",
      foreignField: "id",
      as: "data_objects"
    }
  },
    // Project to return was_generated_by and data object details
  {
    $project: {
      was_generated_by: "$was_generated_by",
      data_objects: {
        $map: {
          input: "$data_objects",
          as: "obj",
          in: {
            url: "$$obj.url",
            data_object_type: "$$obj.data_object_type"
          }
        }
      },
      _id: 0
    }
  }
])