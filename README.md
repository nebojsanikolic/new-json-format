# New JSON format

Rule-data parking configuration for Nebojša Nikolić’s parking app.

This repo defines a **new remote-config JSON shape** to replace today’s flat `zonesData_v2` file. After one cutover (force-update is OK), new parking rules can ship via config without hard-coding them in the app — except brand-new engine capabilities that need a newer app version.

There is **no legacy-format compatibility**. Field names are written for a back-office editor (non-developers), not for matching old keys.

## Start here

| Read this | For |
| --- | --- |
| [`docs/field-reference.md`](docs/field-reference.md) | **Full field reference** — every parameter for teammates |
| [`docs/delivery-manifest.md`](docs/delivery-manifest.md) | **Production delivery** — manifest + shared + per-city + `forceUpdate` |
| [`docs/schema.md`](docs/schema.md) | Concept guide (layers, inheritance, mapping) |
| [`docs/parking-config.schema.json`](docs/parking-config.schema.json) | Machine JSON Schema |
| [`data/parking-config.generated.json`](data/parking-config.generated.json) | Full transformed production data (monolith / tools) |
| [`examples/delivery/`](examples/delivery/) | Tiny sample delivery package (`forceUpdate` demo) |
| [`examples/belgrade-snippet.json`](examples/belgrade-snippet.json) | Small Belgrade excerpt (polygons truncated) |
| [`docs/project-context.md`](docs/project-context.md) | Locked design decisions |
| [`docs/requirements.md`](docs/requirements.md) | Product requirements list |
| [`docs/geojson-import.md`](docs/geojson-import.md) | Import from local GeoJSON (confidential polygons) |

## Architecture (three layers)

```
catalog      countries · cities · operators · currencies · locales
geography    zones → polygons     (polygon.overrides.* beats the zone)
commerce     products + rules + paymentMethods
```

- **Products** describe *what* is sold (duration, price, eligibility, validity).
- **Payment methods** describe *how* to pay, by `type`:
  - `sms` — live today (number, prefix, `messageSlots`, send windows, cooldown)
  - `webview_card` — ready structurally; add a method + app support later **without reshaping** products or zones
- Zones/products hold **`productIds` / `paymentMethodIds`** — string ids pointing at those top-level arrays (references, not nested payloads).
- **Hours** use `"HH:mm"` strings (`"07:00"`, `"24:00"` for end-of-day). Zones have **`enabled`** (`false` = hide in app). Coordinates are rounded to **6 decimal places**.
- **Money** is always `{ "amount": number, "currencyId": string }`.
- **Locales** are maps (`sr-Latn`, `en`, …); grammatical cases nest under the locale.
- **Versioning:** monolith uses `dataVersion` + `minAppVersion`. Production CDN delivery uses **manifest + shared + cities** with per-city `version` and **`forceUpdate`** (see below).

## Production delivery layout

```
manifest.json              # small — always fetched first
shared.json                # locales, currencies, countries, operators
cities/
  city-beograd.json        # city + zones, polygons, products, payments, rules, …
  city-….json
```

- **`forceUpdate: true`** on a city → app must download that city file before relying on it (SMS/price/payment/rules changed). Do not keep serving stale cache for that city.
- **`forceUpdate: false`** → soft / background refresh.
- Manifest root **`forceUpdate`** → global/schema refresh and/or app gate via `minAppVersion`.

Full contract: [`docs/delivery-manifest.md`](docs/delivery-manifest.md).  
Sample (fake Belgrade stub only): [`examples/delivery/`](examples/delivery/).

```bash
python3 scripts/split_parking_config.py \
  -i ~/Downloads/parking-config.from-geojson.json \
  -o ~/Downloads/parking-config-delivery \
  --force-update-cities city-beograd
```

The **monolith** remains optional for tools and transforms; production delivery is the split package.

## Repo layout

```
README.md
data/
  parking-config.generated.json   # full new-format config from production (monolith)
  zonesData_v2.source.json        # snapshot of production input
docs/
  delivery-manifest.md            # CDN delivery + forceUpdate semantics
  field-reference.md
  schema.md
  parking-config.schema.json
  geojson-import.md
  project-context.md
  requirements.md
  legacy-schema.json
examples/
  belgrade-snippet.json
  delivery/                       # minimal manifest + shared + city stub
scripts/
  transform.py                    # regenerates generated JSON + Belgrade example
  geojson_to_parking_config.py    # local GeoJSON → parking-config monolith
  split_parking_config.py         # monolith → manifest + shared + cities
private/                          # gitignored — local GeoJSON / import outputs only
```

**Confidential:** Source GeoJSON (Serbia/Montenegro) and full city polygon dumps must **not** be committed. Keep under `private/` (gitignored) or outside the repo (e.g. `~/Downloads`).

## How the generated file was produced

1. Production source:  
   https://raw.githubusercontent.com/nebojsanikolic/jsonHost/refs/heads/main/zonesData_v2.json  
   (snapshot also stored as `data/zonesData_v2.source.json`)
2. Transform: `python3 scripts/transform.py`
3. Output: `data/parking-config.generated.json`  
   (~98 cities, 211 zones, polygons, timed + full-day products, SMS payment methods, coverage policy stubs)

Features not present in production (night rates, filled price ladders, seasonal overlays, resident permits, fines, live webview card, explicit `coversZoneIds`) are **hooks in the schema** — empty arrays, disabled example payment method, or documented for back office to fill. Ladder shape when used: `{ "stepIndex", "durationMinutes", "price" }` (uneven increments OK; see field reference).

## Regenerate locally

```bash
python3 scripts/transform.py
```

Python 3.10+. Overwrites `data/parking-config.generated.json` and `examples/belgrade-snippet.json`.

### From local GeoJSON (confidential)

Keep GeoJSON and full import output **out of git** (`private/`, `*.geojson` are ignored). See [`docs/geojson-import.md`](docs/geojson-import.md).

```bash
python3 scripts/geojson_to_parking_config.py \
  --rs ~/Downloads/ParkingZonesWithUUID.geojson \
  --me ~/Downloads/parkingZonesMontenegroUUID.geojson \
  -o ~/Downloads/parking-config.from-geojson.json
```

Then split for delivery (local folder only):

```bash
python3 scripts/split_parking_config.py \
  -i ~/Downloads/parking-config.from-geojson.json \
  -o ~/Downloads/parking-config-delivery
```

## Review tips

1. Architecture overview above → then [`docs/field-reference.md`](docs/field-reference.md) for every field.
2. Delivery + `forceUpdate`: [`docs/delivery-manifest.md`](docs/delivery-manifest.md) and [`examples/delivery/`](examples/delivery/).
3. Open [`examples/belgrade-snippet.json`](examples/belgrade-snippet.json) for a readable city excerpt.
4. Spot-check the full monolith against [`docs/parking-config.schema.json`](docs/parking-config.schema.json).
5. Concepts + production mapping: [`docs/schema.md`](docs/schema.md); legacy shape: [`docs/legacy-schema.json`](docs/legacy-schema.json).
