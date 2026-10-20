// Run with mongosh against our local MongoDB instance.

const database = db.getSiblingDB("playground_app");

const validator = {
  $jsonSchema: {
    bsonType: "object",
    required: [
      "_id",
      "provider",
      "sourceService",
      "datasetType",
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
      sourceService: {
        bsonType: "string",
        minLength: 1,
        description: "Stable key identifying the provider's service."
      },
      datasetType: {
        bsonType: "string",
        enum: ["equipment", "parks", "schools"],
        description: "Application category, such as equipment or parks."
      },
      layerId: {
        bsonType: ["int", "null"],
        minimum: 0,
        description: "Source GIS layer ID, or null for sources without layers."
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
  { provider: 1, sourceService: 1, layerId: 1, recordId: 1 },
  { unique: true, name: "source_identity" }
);

print("source_features collection and index are ready.");

const uuidPattern =
  "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$";

const playgroundValidator = {
  $jsonSchema: {
    bsonType: "object",
    additionalProperties: false,
    required: ["_id", "location"],
    properties: {
      _id: {
        bsonType: "string",
        pattern: uuidPattern
      },
      name: {
        bsonType: ["string", "null"],
        minLength: 1
      },
      location: {
        bsonType: "object",
        additionalProperties: false,
        required: ["type", "coordinates"],
        properties: {
          type: {
            enum: ["Point"]
          },
          coordinates: {
            bsonType: "array",
            minItems: 2,
            maxItems: 2,
            items: {
              bsonType: ["double", "int", "long", "decimal"]
            }
          }
        }
      },
      parkSourceId: {
        bsonType: ["string", "null"],
        pattern: uuidPattern
      },
      equipmentSourceIds: {
        bsonType: "array",
        uniqueItems: true,
        items: {
          bsonType: "string",
          pattern: uuidPattern
        }
      }
    }
  }
};

if (database.getCollectionNames().includes("playgrounds")) {
  const result = database.runCommand({
    collMod: "playgrounds",
    validator: playgroundValidator,
    validationLevel: "strict",
    validationAction: "error"
  });

  if (result.ok !== 1) {
    throw new Error("Failed to update playgrounds validation.");
  }
} else {
  database.createCollection("playgrounds", {
    validator: playgroundValidator,
    validationLevel: "strict",
    validationAction: "error"
  });
}

database.playgrounds.createIndex(
  { location: "2dsphere" },
  { name: "playground_location" }
);

database.playgrounds.createIndex(
  { equipmentSourceIds: 1 },
  {
    name: "unique_playground_equipment",
    unique: true,
    partialFilterExpression: {
      "equipmentSourceIds.0": { $exists: true }
    }
  }
);

print("playgrounds collection and index are ready.");
