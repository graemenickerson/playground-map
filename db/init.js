// Run with mongosh against our local MongoDB instance.

const database = db.getSiblingDB("playground_app");

const validator = {
  $jsonSchema: {
    bsonType: "object",
    required: [
      "_id",
      "provider",
      "layerId",
      "recordId",
      "attributes",
      "geometry",
      "importedAt"
    ],
    properties: {
      _id: {
        bsonType: "string",
        pattern:
          "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
        description: "Application-generated UUID v4 string."
      },
      provider: {
        bsonType: "string",
        minLength: 1,
        description: "The organization supplying the record."
      },
      layerId: {
        bsonType: "int",
        description: "The city's map layer ID."
      },
      recordId: {
        bsonType: "string",
        minLength: 1,
        description: "The source record's OBJECTID, stored as a string."
      },
      attributes: {
        bsonType: "object",
        description: "Original source properties without renaming fields."
      },
      geometry: {
        bsonType: ["object", "null"],
        description: "GeoJSON geometry in WGS84, or null if unavailable."
      },
      importedAt: {
        bsonType: "date",
        description: "When our importer retrieved this record."
      }
    }
  }
};

if (database.getCollectionNames().includes("source_features")) {
  const result = database.runCommand({
    collMod: "source_features",
    validator,
    validationLevel: "strict",
    validationAction: "error"
  });

  if (result.ok !== 1) {
    throw new Error("Failed to update source_features validation.");
  }
} else {
  database.createCollection("source_features", {
    validator,
    validationLevel: "strict",
    validationAction: "error"
  });
}

database.source_features.createIndex(
  { provider: 1, layerId: 1, recordId: 1 },
  { unique: true, name: "source_identity" }
);

print("source_features collection and index are ready.");
