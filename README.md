# Victoria Playground Map

A learning project for finding playgrounds in Victoria, BC.

The app displays playground locations using React and Mapbox, backed by
a small Flask API and MongoDB. Development currently focuses on local
use and City of Victoria parks. Amenities, filtering, school playgrounds,
and submitting corrections are future work.

## Stack

- React, TypeScript, and Vite
- Mapbox GL JS for the map
- Zod for validating API responses
- Flask, PyMongo, and Pydantic
- MongoDB running in Docker

The frontend and Flask run directly on your machine. Only MongoDB runs
in Docker.

## Requirements

- Python 3.13, the version used during development
- Node.js 22.12 or newer and npm
- Docker with Docker Compose
- Make
- A public Mapbox access token beginning with `pk.`

## Local setup

Run commands from the repository root unless otherwise noted.

### Install dependencies

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
npm --prefix frontend ci
```

### Start and initialize MongoDB

```bash
docker compose up -d
docker compose cp db/init.js mongo:/tmp/playground-init.js
docker compose exec -T mongo \
  mongosh playground_app --quiet --file /tmp/playground-init.js
```

The initialization script creates collection validators and indexes.
MongoDB data persists in the Compose named volume.

### Import the city data

```bash
.venv/bin/python -m scripts.import_sources
```

The importer reads equipment and park records from the
[City of Victoria parks GIS service](https://maps.victoria.ca/server/rest/services/OpenData/OpenData_Parks/MapServer).

Source GIS layer IDs are retained as provenance. They are separate from
the categories used to colour playground pins.

Re-running the importer refreshes existing source records while
preserving their application UUIDs. It does not rebuild saved playgrounds.

### Check reviewed groups

`scripts/playground_overrides.json` records manually reviewed equipment
groups, including a Beacon Hill group and a playground on former school
grounds.

These selections reference UUIDs from the database where they were
reviewed. Before populating a fresh database, update those references
to match your imported records.

Alternatively, use an empty JSON array (`[]`) in that file to start with
automatic grouping only. Unresolved equipment can then be inspected as
red review pins.

### Preview and save playgrounds

Preview without database writes:

```bash
.venv/bin/python -m scripts.populate_playgrounds
```

Save all valid candidates and generate the map's equipment review file:

```bash
.venv/bin/python -m scripts.populate_playgrounds \
  --save \
  --review-output frontend/public/equipment-review.json
```

Use `--save-reviewed` instead of `--save` to save only manually reviewed
groups.

Already-assigned equipment is skipped or reported for review. A unique
MongoDB index prevents an equipment record from belonging to more than
one playground.

### Configure Mapbox

```bash
cp frontend/.env.example frontend/.env.local
```

Set this value in `frontend/.env.local`:

```dotenv
VITE_MAPBOX_ACCESS_TOKEN=your_public_mapbox_token
```

Vite exposes `VITE_` variables to browser code. Use a public token;
keep secret tokens out of frontend configuration.

Restart Vite after changing environment variables.

### Run the app

In one terminal:

```bash
make dev
```

In another terminal:

```bash
make frontend
```

Open http://127.0.0.1:5173.

Flask runs on http://127.0.0.1:5001. Vite proxies `/api` requests to Flask.

## Data model and grouping

`source_features` stores imported records and their original attributes,
geometry, source identity, and import time.

`playgrounds` stores the application-facing playgrounds: a UUID, optional
name, location, site category, optional park reference, and equipment
references. Equipment references are omitted from API responses.

Automatic grouping:

1. Finds the park containing each equipment point.
2. Connects equipment points within 15 metres of one another.
3. Rejects a group if any equipment pair exceeds 50 metres.

Reviewed groups can specify a different maximum spread. The reviewed
Beacon Hill group uses 60 metres.

Locations use GeoJSON coordinates in `[longitude, latitude]` order.

## Map colours

| Colour | Meaning |
| --- | --- |
| Green | Park playground |
| Yellow | Pop-up playground |
| Purple | School playground |
| Gray | Unknown category |
| Red | Individual equipment point needing review |

School support is deferred. Red points come from a generated review
snapshot rather than saved playground documents. Regenerate the snapshot
and refresh the page after resolving equipment.

## API

- `GET /api/health` — application health response
- `GET /api/playgrounds` — saved playgrounds
- `GET /api/playgrounds?limit=100` — specify a limit from 1 to 500

The playground response contains `items`, `limit`, and `hasMore`.
The default limit is 100. The frontend currently loads the default page.

The API currently provides anonymous, read-only access. Data writes are
performed through local scripts. Production deployment and authentication
are outside the current scope.

Backend defaults:

| Variable | Default |
| --- | --- |
| `MONGODB_URI` | `mongodb://127.0.0.1:27017` |
| `MONGODB_DATABASE` | `playground_app` |

Set these in the shell running Flask or the scripts when overriding them.

## Useful commands

Inspect source data:

```bash
.venv/bin/python -m scripts.examine_sources
```

Open an interactive MongoDB shell:

```bash
docker compose exec mongo mongosh playground_app
```

Check frontend types or build:

```bash
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

Stop MongoDB while retaining its data:

```bash
docker compose down
```

## Project layout

- `backend/` — Flask API and Pydantic models
- `db/` — MongoDB validators and indexes
- `scripts/` — imports, inspection, and playground generation
- `frontend/` — React app, Zod schemas, and Mapbox component
- `plan.md` — project planning notes
