# Parking config format

Remote **rule-data** for Serbia / Montenegro parking apps — zones, prices, SMS, hours, polygons — shipped as JSON so cities can update **without** a full force-refresh of every file.

This repo is the **schema, docs, and CLI**. Editing UI lives in a separate private studio (`parking-config-studio`).

No legacy-key compatibility. Names are for back-office editors, not for mirroring old `zonesData_v2` keys.

---

## Why

| Before | After |
| --- | --- |
| One flat file for all cities | Small `manifest.json` → `shared.json` + only changed city files |
| App update for every rule tweak | Config publish; app update only for new engine capabilities |
| Opaque legacy keys | Explicit products, payment methods, money, locales |

---

## Paths

| Goal | Go here |
| --- | --- |
| Every field | [`docs/field-reference.md`](docs/field-reference.md) |
| CDN / `forceUpdate` / checksums | [`docs/delivery-manifest.md`](docs/delivery-manifest.md) |
| Concepts (layers, inheritance) | [`docs/schema.md`](docs/schema.md) |
| Machine schema | [`docs/parking-config.schema.json`](docs/parking-config.schema.json) |
| GeoJSON → config (local, confidential) | [`docs/geojson-import.md`](docs/geojson-import.md) |
| Tiny delivery stub | [`examples/delivery/`](examples/delivery/) |
| Readable city excerpt | [`examples/belgrade-snippet.json`](examples/belgrade-snippet.json) |

---

## Shape (sketch)

```
catalog      countries · cities · operators · currencies · locales · holidays
geography    zones → polygons     (polygon.overrides.* wins over zone)
commerce     products · paymentMethods · rules
```

Holidays, closures, `pricing.byDay`, and `free_initial_minutes`: [docs/holidays-and-time-rules.md](docs/holidays-and-time-rules.md).

Products = *what* is sold. Payment methods = *how* (today: `sms`; `webview_card` ready structurally). Zones link by id arrays — no nested payloads.

---

## Compact examples

Coordinates are **`[lat, lon]`** (lat-first, 6 dp) — not GeoJSON lon-first, not `{ latitude, longitude }` objects. Truncated samples use `"ringTruncated": true` (no sentinel vertex).

```json
"ring": [[44.814512, 20.45659], [44.814231, 20.457672]],
"ringTruncated": true
```

```json
"price": { "amount": 80, "currencyId": "rsd" }
```

```json
"ladder": [
  { "stepIndex": 1, "durationMinutes": 60, "price": { "amount": 80, "currencyId": "rsd" } },
  { "stepIndex": 2, "durationMinutes": 30, "price": { "amount": 40, "currencyId": "rsd" } }
]
```

Manifest integrity (exact UTF-8 file bytes):

```json
"checksum": "sha256:e0f0a24b0b6465de5721a7eb8e6c13712ed3ce0201fec69018a3da7234297c5d",
"contentHash": "sha256:e0f0a24b0b6465de5721a7eb8e6c13712ed3ce0201fec69018a3da7234297c5d"
```

Also: hours as `"HH:mm"` / `"24:00"` · locales as maps (`sr-Latn`, `en`, …) · envelope `schemaVersion` separate from `mainVersion` / city / shared content versions.

---

## Delivery

```
manifest.json          ← always fetched first
shared.json            ← locales, currencies, countries, operators
cities/{cityId}.json   ← one city slice
```

- City `forceUpdate: true` → download before parking in that city (price / SMS / rules).
- `false` → soft / background refresh.
- Root `forceUpdate` → global / schema gate (+ `minAppVersion` when needed).

Details: [`docs/delivery-manifest.md`](docs/delivery-manifest.md).

---

## CLI

Python 3.10+. Keep source GeoJSON and full polygon dumps **out of git** (`private/`, `*.geojson`).

**GeoJSON → monolith** (local paths only):

```bash
python3 scripts/geojson_to_parking_config.py \
  --rs ~/Downloads/ParkingZonesWithUUID.geojson \
  --me ~/Downloads/parkingZonesMontenegroUUID.geojson \
  -o ~/Downloads/parking-config.from-geojson.json
```

**Monolith → delivery package:**

```bash
python3 scripts/split_parking_config.py \
  -i ~/Downloads/parking-config.from-geojson.json \
  -o ~/Downloads/parking-config-delivery \
  --force-update-cities city-beograd
```

**Regenerate checked-in transform** (from `data/zonesData_v2.source.json`):

```bash
python3 scripts/transform.py
```

---

## Studio (separate repo)

**Parking Config Studio** (private) — map editor, Validate, Publish wizard, folder/ZIP export.  
This repo stays the source of truth for **format + scripts + docs**; the studio consumes and emits the same shape.

---

## Repo map

| Path | Role |
| --- | --- |
| `docs/` | Field reference, delivery contract, schema |
| `scripts/` | Transform, GeoJSON import, split for CDN |
| `data/` | Generated monolith + source snapshot |
| `examples/` | Snippet + minimal delivery stub |
| `private/` | Gitignored local GeoJSON / outputs |

---

## Status notes

- Cutover from `zonesData_v2` is one-time (force-update OK).
- Schema hooks (night rates, seasonal overlays, `coversZoneIds`, webview card, …) may be empty until back office fills them — see field reference.
- Full polygons are confidential; only truncated samples ship in examples.
