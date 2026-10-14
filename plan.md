# Victoria Playground Map

Status: planning — local development first.

## Purpose

Build a playground discovery app for the City of Victoria, BC, while learning MongoDB document modelling, geographic queries, and indexes. Start within municipal boundaries; expansion into Greater Victoria can follow later.

## Agreed stack

- Frontend: React, TypeScript, Vite, and Mapbox GL JS.
- Backend: a small Flask JSON API using PyMongo.
- Validation: Python type hints and Pydantic on the backend; TypeScript and Zod on the frontend.
- Database: MongoDB.
- Data import: Python tooling for Victoria's municipal datasets.
- One repository containing frontend/, backend/, and scripts/.

## Phase 1: browse and filter

- Map of Victoria with playground locations and a matching list.
- Select a playground from the map or list to view its details.
- Details include name, equipment, amenities, source, and verification date when available.
- Amenity filters, initially washrooms and drinking water if source completeness supports them.
- Equipment filters after inspecting the source records.
- Keep map, list, selection, and filters consistent.
- Usable mobile and desktop layouts with loading, empty, and error states.
- Distinguish confirmed presence, confirmed absence, and unknown amenities.

Name search, current-location search, and external directions links remain optional scope decisions. No accounts or favourites are planned.

## Phase 2: corrections and review

- Submit a suggested correction from a playground's details panel.
- Store submissions separately from published playground records.
- Review and approve or reject corrections before changing public data.
- Decide the review interface and any authentication or abuse controls when this phase begins.

## Data sources and preparation

Use City of Victoria municipal data as the initial source:

- Parks service: https://maps.victoria.ca/server/rest/services/OpenData/OpenData_Parks/MapServer
- Parks and Open Spaces: layer 50.
- Playground Equipment: layer 20.
- Drinking Fountains: layer 17.
- Playground Surface: layer 23.
- Park Parking Lots: layer 46.
- Washroom information: https://www.victoria.ca/parks-recreation/our-parks/public-washrooms

Inspect actual records, coded values, lifecycle status, field completeness, licence, and attribution requirements before importing or promising filters.

Equipment assets are not individual playgrounds, and one park may contain multiple playgrounds. Establish grouping rules using locations, park associations, and manual review where necessary.

Request or transform coordinates into WGS84 longitude/latitude for GeoJSON. Preserve source identifiers and import dates. Do not describe an amenity elsewhere in a park as being directly beside the playground. Geographic distance must not be labelled walking distance.

Imports should be repeatable, use stable identifiers, preserve curated overrides, and flag removed or changed source records for review. Run imports manually during phase 1; scheduling is deferred.

## MongoDB design

Start with a playgrounds collection containing one document per playground:

- Stable identifier, name, municipality, and park association.
- GeoJSON Point location; coordinate order is longitude, latitude.
- Embedded equipment and amenity summaries where appropriate.
- Unknown amenity values represented explicitly.
- Source references, import timestamp, and verification dates when available.
- Curated overrides kept distinct from imported values.

Use a 2dsphere index on location and unique source identifiers where appropriate. Add further indexes based on actual queries.

Separate parks or shared amenity collections may be useful after inspecting the source. Add a corrections collection in phase 2.

### Proposed document structure — for discussion

- playgrounds: one application-owned document per playground, with a stable ID, park summary/reference, GeoJSON location, embedded equipment, amenity summaries, and source metadata.
- parks: park names, source identifiers, and boundary polygons if needed for import grouping and map outlines.
- corrections: deferred to phase 2; separate records rather than a growing array inside each playground.

Embed equipment because it belongs to a playground and is usually read with its details. A park reference plus an embedded name avoids a join for ordinary browsing; imports must keep that name synchronized.

Amenity summaries should use present/absent/unknown status and include context (at the playground, in the park, or nearby), evidence, and verification dates when available. A park-level washroom flag does not establish its exact location or distance. Never infer absence solely from an empty source layer.

Keep curated overrides separate from source-derived values and derive effective filterable fields during import/update processing. Application IDs must survive regrouping or changes to individual city equipment IDs.

Queries to explore: proximity ordered by distance, playground points within the map viewport, combined amenity filters, equipment matching, projected list responses, and aggregation counts by equipment or municipality. Add schema validation for required fields and valid statuses when implementing the collection.

### Playground document v1 — proposed contract

One document represents one physical playground, not one park or one equipment asset. The following is fictional sample data in MongoDB shell notation; timestamps are BSON dates and the identifier is an application-generated ObjectId.

```js
{
  _id: ObjectId("507f1f77bcf86cd799439011"),
  schemaVersion: 1,
  name: "Example Playground",
  municipality: "Victoria",
  description: null,
  park: {
    id: ObjectId("507f1f77bcf86cd799439012"),
    name: "Example Park"
  },
  location: {
    type: "Point",
    coordinates: [-123.3656, 48.4284]
  },
  equipment: [
    {
      type: "swings",
      sourceRef: "city-equipment-example-001"
    }
  ],
  amenities: {
    washroom: {
      status: "present",
      context: "in_park",
      sourceRefs: ["city-park-example-001"],
      verifiedAt: null
    },
    drinkingWater: {
      status: "unknown",
      context: null,
      sourceRefs: [],
      verifiedAt: null
    }
  },
  sources: [
    {
      ref: "city-equipment-example-001",
      provider: "city_of_victoria",
      layerId: 20,
      recordId: "example-equipment-001"
    },
    {
      ref: "city-park-example-001",
      provider: "city_of_victoria",
      layerId: 50,
      recordId: "example-park-001"
    }
  ],
  importedAt: ISODate("2026-10-13T00:00:00Z"),
  updatedAt: ISODate("2026-10-13T00:00:00Z")
}
```

| Property | Shape | Purpose and rule |
| --- | --- | --- |
| _id | ObjectId | Stable application identity; retain across imports rather than generating a new ID each time. |
| schemaVersion | Integer | Identifies this document contract as the structure evolves. |
| name | Non-empty string | Display name; derived names must be distinguishable from official names during import preparation. |
| municipality | String | Municipality name, initially Victoria. |
| description | String or null | Optional factual description; null means unavailable. |
| park | Object or null | Park reference and cached display name; null if association is unresolved. |
| location | GeoJSON Point | Required, verified playground position in WGS84; longitude first. It represents the playground, not the centre of the entire park. |
| equipment | Array of objects | Embedded known assets with normalized type and source reference; an empty array means none recorded, not confirmed absence. |
| amenities | Object keyed by amenity | Initially washroom and drinkingWater, both present even when unknown. |
| sources | Array of objects | Evidence identifiers used by embedded equipment and amenities; references must resolve within this document. |
| importedAt | Date or null | Last successful source refresh for this document; null for a purely manual record. |
| updatedAt | Date | Last application update, including imports. This is not a verification date. |

Amenity status values are present, absent, and unknown. Context values are at_playground, in_park, nearby, or null when unspecified. Absence requires explicit evidence; missing records produce unknown. verifiedAt records an actual verification, not an import date. Optional source URLs can be retained alongside source identifiers.

For v1, use a point for each playground. A footprint polygon can be an optional later addition after examining the surface layer; park boundaries belong to parks. Do not invent footprint or accessibility data.

Equipment types will be normalized after inspecting source values; use unknown for an unclassified asset and retain the original value when needed. Age ranges, surface type, fencing, shade, accessibility descriptions, photos, and precise amenity locations remain extensions to discuss once evidence is available.

The sample represents effective browseable values. Before supporting curated edits, define separate imported values and overrides so reimporting cannot erase reviewed changes. Playground grouping needs a stable mapping to application IDs; equipment record IDs alone are not playground IDs.

Validate required properties, status/context enums, coordinate ranges, and referenced source entries during import. Use database schema validation for structure and types. The API will serialize ObjectId values as strings and dates as ISO timestamps.

## Flask API

- GET /api/health — basic service health.
- GET /api/playgrounds — browse using map bounds or proximity, with amenity filters.
- GET /api/playgrounds/<id> — full details.

Validate coordinates and filter values, limit query size, and define consistent JSON responses and errors. Serialize MongoDB identifiers and dates into API-friendly values. Use a shared PyMongo client within each application process.

## Types and runtime validation

Static types help check application code during development. Runtime validators check the actual data entering the application. Python annotations and TypeScript types alone do not validate external data.

### Backend: Python and Pydantic

- Use Python type hints throughout backend and import code, with a static checker such as Pyright or mypy; select the checker during scaffolding.
- Define Pydantic models for normalized playground data, request parameters, and API responses.
- Explicitly invoke validation in Flask routes and importer code; Flask does not automatically validate these models.
- Validate normalized imports before writing to MongoDB, including required fields, amenity enums, coordinate ranges, and source-reference consistency.
- Configure strict validation for normalized data where appropriate. Parse query-string numbers deliberately because HTTP query parameters arrive as strings.
- Reject unexpected fields on input contracts where appropriate and return consistent client validation errors. Invalid stored data or response construction is a server-side error, not a client error.
- Keep MongoDB schema validation as an additional check on persisted structure and types.

### Frontend: TypeScript and Zod

- Use TypeScript for application code and Zod for runtime validation at external data boundaries.
- Define Zod schemas for API payloads and infer their TypeScript types with z.infer rather than maintaining duplicate interfaces.
- Treat unvalidated API JSON as unknown, then parse it in the API client before passing it to components.
- Handle invalid responses as a controlled error state rather than asserting that fetched JSON has the expected type.
- Once parsed, use the typed data throughout React without repeated validation in individual components.
- Reuse this approach for correction form inputs in phase 2; frontend checks do not replace backend validation.

### Database documents and API contracts

Keep persistence and API models explicit. MongoDB stores ObjectId and BSON date values; JSON responses expose string IDs and ISO timestamps. Define a conversion layer and validate the resulting response against the API model. List and detail endpoints may expose different fields.

Start with explicit Pydantic and Zod schemas rather than introducing schema generation. Keep their API field names, enums, nullability, and required properties aligned. Use shared valid and invalid response fixtures and meaningful contract checks to detect drift, including ID/date serialization. Explore generation only if maintaining the contracts becomes burdensome.

## Local infrastructure

Browser -> Vite frontend -> Flask API -> MongoDB

The browser also requests map resources from Mapbox. Python import tooling reads city data and writes to MongoDB.

- Run Vite and Flask as separate local development processes.
- Configure Vite to proxy /api to Flask.
- Keep backend dependencies in a Python virtual environment with an explicit dependency file.
- Run only MongoDB in Docker Compose; Flask, Vite, and import tooling run directly on the host.
- Persist MongoDB data in a named volume.
- Keep the MongoDB connection string in backend configuration.
- Provide example environment files without secrets.
- Configure the browser Mapbox token with suitable public scopes and localhost URL restrictions.
- Document setup, import, and run commands in README.md.

Application and database processes will run locally. Mapbox and source-data imports still require internet access. Production hosting, domains, CI/CD, scheduled cloud imports, and production operations are deferred.

## Working approach

Use the IDE's file-editing and diff review workflow for proposed project changes. Do not use shell scripts to create or rewrite project source files. Import tooling is application functionality and will be implemented as reviewable source files.

## Implementation sequence

1. Finalize phase 1 features and the proposed document structure.
2. Inspect Victoria records and establish playground grouping and amenity rules.
3. Scaffold React/Vite and Flask with a working local API connection.
4. Connect local MongoDB and create a small verified sample dataset.
5. Implement repeatable imports and geographic indexes.
6. Build the map, list, details panel, and agreed filters.
7. Verify import repeatability, spatial queries, missing-data handling, and mobile usability.
8. Document how to run the complete application locally.

## Open decisions

- Include name search or current-location search in phase 1?
- Which filters have sufficiently complete source data?
- Final playground grouping rules, amenity context, and embedding/reference choices after inspecting source records.
- Final map/list layout and detail fields.
