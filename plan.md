# Victoria Playground Map

Status: local foundation and basic map browsing implemented.

## Purpose

Build a playground discovery app for the City of Victoria, BC, while learning MongoDB document modelling, geographic queries, and indexes. Start within municipal boundaries; expansion into Greater Victoria can follow later.

## Agreed stack

- Frontend: React, TypeScript, Vite, and Mapbox GL JS.
- Backend: a small Flask JSON API using PyMongo.
- Validation: Python type hints and Pydantic on the backend; TypeScript and Zod on the frontend.
- Database: MongoDB.
- Data import: Python tooling for Victoria's municipal datasets.
- One repository containing frontend/, backend/, and scripts/.

## Implementation progress

The initial implementation was narrowed to playground locations.
Unknown names, categories, and park associations are acceptable.
Name search, child-age-range filtering, and a park-level washroom
filter are implemented.

Completed:

- MongoDB running locally through Docker Compose.
- Collection validators, geographic index, and unique equipment ownership.
- Repeatable city park and equipment imports preserving source UUIDs.
- Playground generation using 15-metre connections and a 50-metre
  maximum pairwise spread.
- Reviewed grouping overrides, including a 60-metre limit for one
  Beacon Hill group.
- Saving valid candidates while preventing equipment reuse.
- Read-only Flask API with validated query parameters and JSON errors.
- React map and basic list with Zod response validation.
- Coloured playground pins and red equipment review pins.
- Floating search panel with name search and a park-level washroom filter.
- Reusable three-way age selector: Any age, Ages 2–5, and Ages 5–12.
- Immediate filtering for age and washroom changes.
- Name search debounced by 300 milliseconds after the last keystroke.
- Cancellation of superseded requests, with previous results retained
  while loading or after a failed request.
- Map instance and viewport preserved when filtered results change.
- README with local setup instructions.
- GitHub remote repository.

Current local dataset: 51 playgrounds covering 194 active equipment
records, with no equipment assigned more than once and no unresolved
equipment in the review snapshot.

The implemented playground document currently contains:
_id, name, siteType, location, parkSourceId, and equipmentSourceIds.
Names and park references may be null. Equipment references are excluded
from API responses.

The richer document structure below remains a proposed future design.

Next:

1. Share selected playground state between the map and list.
2. Support selection from either a pin or list item.
3. Highlight the selected item and focus its map location.
4. Add a simple details panel using available data.
5. Verify selection, missing-data handling, and mobile usability.

Deferred: neighbourhood search, device-location distance filtering,
other amenities and equipment-type filters, school playground processing,
correction submissions, authentication, and production deployment.

Known limitations:

- Population inserts playgrounds but does not synchronize existing ones
  after source changes or regrouping.
- Reviewed overrides reference local source UUIDs and need adjustment
  for a fresh database.
- The frontend loads the default API page of up to 100 playgrounds.
- Equipment review pins use a generated JSON snapshot.
- Import change/removal handling and repeat-population verification
  remain outstanding.

## Phase 1: browse and filter

- Map of Victoria with playground locations and a matching list.
- Select a playground from the map or list to view its details.
- Details include name, equipment, amenities, source, and verification date when available.
- Case-insensitive partial name search across playground names and
  associated park names and aliases.
- Filter by the child's age range using recorded equipment age ranges.
- Filter for a recorded washroom in the associated park.
- Other amenity and equipment-type filters are deferred.
- Keep map, list, selection, and filters consistent.
- Usable mobile and desktop layouts with loading, empty, and error states.
- Distinguish confirmed presence, confirmed absence, and unknown amenities.

Neighbourhood search and device-location distance filtering are planned
for a later increment, as described below. External directions links
remain an optional scope decision. No accounts or favourites are planned.

### Current search and filter requirements

- Name search matches playground names, associated park names, and park
  aliases. Missing names must not prevent browsing without a search term.
- Child-age filtering uses PlayEquipmentAge, not installation date,
  PlaygroundAge, or the age of the playground itself.
- Include a playground when at least one associated equipment record's
  age range covers the whole selected range.
- Choices are Any age, Ages 2–5, and Ages 5–12.
  Ages 2–5 matches recorded ranges 2–5 and 2–12.
  Ages 5–12 matches recorded ranges 5–12 and 2–12.
  Sharing only a boundary age does not establish a match.
- Missing equipment age ranges remain unknown. They do not establish an
  age match or prove that the playground is unsuitable.
- A recorded equipment age range does not guarantee the suitability of
  every feature or accessibility for an individual child.
- Label the washroom filter as "Washroom in park". It uses the associated
  park's Washroom value, not an assumption about the playground itself.
- Only a recorded Yes satisfies the washroom filter. Missing park
  references or washroom values remain unknown.
- Combine active search and filters: results must satisfy each active
  condition. Keep map pins and list results consistent.
- Equipment-type filters are deferred. EquipmentType is empty in the
  inspected data; comments provide partial evidence of swings and a slide,
  but missing mentions do not establish absence.
- Search controls float above the map. The form can be collapsed.
- Age selection uses a connected three-way toggle with one active segment.
- Age and washroom changes apply immediately. Name changes apply after
  300 milliseconds without another keystroke; Enter applies immediately.
- Filter changes, Clear, and unmounting cancel pending text-search timers.
- Clear restores an empty name, Any age, and no washroom restriction.
- Show loading, result-count, empty, and error states. Retain previous
  results during requests and label them as previous results after errors.
- Preserve the user's map position when results change; automatically
  frame playground results only on their initial load.

### Later: neighbourhood search

- Allow the same search field to match neighbourhood names such as
  James Bay and Fairfield, alongside playground and park names.
- Find an authoritative neighbourhood boundary dataset and review its
  licence, identifiers, names, and coordinate system before importing.
- Assign playground neighbourhoods using point-in-polygon checks against
  their locations. Do not infer neighbourhoods from park names.
- Retain a stable neighbourhood identifier, display name, and source
  provenance. Normalize case and whitespace for searching; introduce
  aliases only where supported.
- Define how boundary points, overlapping matches, and unmatched
  locations are handled. Unresolved neighbourhoods remain unknown.
- Refresh derived neighbourhood assignments when locations or boundaries
  change.
- Extend import processing, database fields, API contracts, and frontend
  validation when implementing this feature.

### Later: distance from device location

- Request browser geolocation only after the user chooses
  "Use my location".
- Use the reported coordinates as a temporary search origin. Do not
  persist device location in playground documents or ordinary logs.
- Let the user choose a radius. Radius options and the UI remain to be
  decided.
- Use the existing MongoDB 2dsphere index for radius filtering and
  nearest-first results.
- Measure straight-line distance and label it accordingly; do not present
  it as walking distance.
- Validate longitude, latitude, and radius in Flask. Apply geographic
  filtering and other active filters before limiting results.
- Handle permission denial, timeout, unavailable location, and poor
  reported accuracy without breaking name search or other filters.
- Allow clearing the location filter and requesting an updated location.
  Continuous location tracking is outside scope.
- Browser geolocation requires a secure context; localhost supports
  development, and a future hosted version will require HTTPS.

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

### Source identity and application categories

Preserve municipal layer IDs as source metadata, not application categories
or Mapbox display-layer identifiers.

Raw source records live in source_features and include:

- _id: application-generated UUID v4 string.
- provider: source organization, initially city_of_victoria.
- sourceService: stable service key, initially parks.
- datasetType: application category, initially equipment or parks.
- layerId: original municipal layer ID.
- recordId: original source record ID, stored as a string.
- attributes: original source properties.
- geometry: GeoJSON in WGS84, or null when unavailable.
- importedAt: timezone-aware retrieval timestamp.

Source configuration maps each provider/service to its API URL and maps
application dataset categories to municipal layer IDs. For Victoria's
parks service, equipment maps to 20 and parks maps to 50.

Identify source records uniquely by:
provider + sourceService + layerId + recordId.

datasetType describes the record; it is not part of its source identity.
Generate UUIDs only on insertion and preserve them during repeat imports.

Normalize source records into application playground documents separately.
Frontend behavior uses application fields; Mapbox display layers use our
own names, such as playground-pins and park-outlines.

During this early development reset, update the model, database validator,
unique index, and importer before dropping playground_app. Then rerun
db/init.js and the importer. Do not delete other databases or Docker volumes.

Current source findings: the equipment import contains 194 asset records,
not 194 playgrounds. EquipmentType is empty throughout the inspected data,
so equipment-type filters require additional evidence.

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

- source_features: original municipal records with source identity,
  application dataset category, geometry, and import timestamp.
- playgrounds: one application-owned document per playground, with a stable ID, park summary/reference, GeoJSON location, embedded equipment, amenity summaries, and source metadata.
- parks: park names, source identifiers, and boundary polygons if needed for import grouping and map outlines.
- corrections: deferred to phase 2; separate records rather than a growing array inside each playground.

Embed equipment because it belongs to a playground and is usually read with its details. A park reference plus an embedded name avoids a join for ordinary browsing; imports must keep that name synchronized.

Amenity summaries should use present/absent/unknown status and include context (at the playground, in the park, or nearby), evidence, and verification dates when available. A park-level washroom flag does not establish its exact location or distance. Never infer absence solely from an empty source layer.

Keep curated overrides separate from source-derived values and derive effective filterable fields during import/update processing. Application IDs must survive regrouping or changes to individual city equipment IDs.

Queries to explore: proximity ordered by distance, playground points within the map viewport, combined amenity filters, equipment matching, projected list responses, and aggregation counts by equipment or municipality. Add schema validation for required fields and valid statuses when implementing the collection.

### Playground document v1 — proposed contract

One document represents one physical playground, not one park or one equipment asset. The following is fictional sample data in MongoDB shell notation; timestamps are BSON dates and application identifiers are UUID v4 strings.

```js
{
  _id: "daaf12af-fcce-4703-8503-f81175bac281",
  schemaVersion: 1,
  name: "Example Playground",
  municipality: "Victoria",
  description: null,
  park: {
    id: "387ac2e8-726c-4bfa-ae42-a735e92b694a",
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
      sourceService: "parks",
      datasetType: "equipment",
      layerId: 20,
      recordId: "example-equipment-001"
    },
    {
      ref: "city-park-example-001",
      provider: "city_of_victoria",
      sourceService: "parks",
      datasetType: "parks",
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
| _id | UUID v4 string | Stable application identity; retain across imports rather than generating a new ID each time. |
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

Validate required properties, UUIDs, status/context enums, coordinate ranges,
and referenced source entries during import. Use database schema validation
for structure and types. IDs remain strings; serialize dates as ISO timestamps.

## Flask API

Currently implemented: GET /api/health and GET /api/playgrounds,
with optional list parameters:

- q: case-insensitive literal partial name search, up to 100 characters.
- age: 2-5 or 5-12; omit for no age restriction.
- washroom: true requires a recorded park washroom; false or omitted
  applies no washroom restriction.
- limit: integer from 1 to 500, defaulting to 100.

Combine active conditions before sorting and limiting results.
Reject unsupported or repeated parameters and invalid values.

The list response contains items, limit, and hasMore.
Reads are anonymous; writes are performed through local scripts.

The following describes the planned API beyond the current implementation:

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

Keep persistence and API models explicit. Application IDs are UUID strings
in both MongoDB and JSON responses. MongoDB stores BSON dates; JSON exposes
ISO timestamps. Define a conversion layer and validate the resulting response
against the API model. List and detail endpoints may expose different fields.

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

Propose one file at a time. Show complete new files or complete proposed diffs
inline in chat before writing them, and wait for approval. IDE pre-write diff
display is not guaranteed by this integration. Apply approved changes with
the file-editing tool rather than shell scripts.

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

- Select a neighbourhood boundary source for later neighbourhood search.
- Choose radius options and accuracy handling for later location filtering.
- Final playground grouping rules, amenity context, and embedding/reference choices after inspecting source records.
- Final map/list layout and detail fields.
