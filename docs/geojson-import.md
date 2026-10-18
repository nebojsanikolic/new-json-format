# GeoJSON → parking-config import

Convert local confidential parking-zone GeoJSON FeatureCollections into the
[parking-config](field-reference.md) format.

**Do not commit GeoJSON or generated full configs.** Keep them under
`private/` (gitignored) or outside the repo (e.g. `~/Downloads`).

## Inputs (local)

| Flag | Typical path | Country |
| --- | --- | --- |
| `--rs` | `~/Downloads/ParkingZonesWithUUID.geojson` | Serbia (`rs`) |
| `--me` | `~/Downloads/parkingZonesMontenegroUUID.geojson` | Montenegro (`me`) |

Each feature is one polygon. Features sharing `(city_id, zone_id)` become one
zone with multiple `polygons[]`. Features missing `zone_id` get a synthetic
zone id from the zone name (temporary lots, etc.).

## Run

```bash
python3 scripts/geojson_to_parking_config.py \
  --rs ~/Downloads/ParkingZonesWithUUID.geojson \
  --me ~/Downloads/parkingZonesMontenegroUUID.geojson \
  -o ~/Downloads/parking-config.from-geojson.json \
  --sample-output private/parking-config.from-geojson.sample.json \
  --sample-cities city-beograd city-podgorica
```

Optional: `--data-version`, `--min-app-version`.

## Property mapping (summary)

| GeoJSON | parking-config |
| --- | --- |
| `city_id`, `is_in`, `city_short_name`, `city_coordinate` | `cities[]` (+ `countryId` from file) |
| `zone_id`, `colour`, names/descriptions/`info_note:*` | `zones[]` (`enabled: true`) |
| `polygon_id` + geometry ring | `polygons[]` (`enabled: true`, `ring` as `[lat, lon]` @ 6 dp) |
| `fee:conditional` | `zones[].paymentWindows` (`HH:mm`). Supports `yes @ Mo-Fr 07:00-21:00` and parenthesized forms like `yes @ (Fr-Su 06:00-14:00)`. Days outside the windows stay free. |
| `base_rate` / `base_unit` | timed `products[].price` + `pricing` |
| `extension_rate(_2)` / `extension_unit(_2)` / `special_extension_*` | `pricing.ladder[]` (`stepIndex`, `durationMinutes`, `price`) |
| `daily_rate` + `payment:sms:daily` | `products` `kind: full_day` + SMS method. Zone may be `fullDayOnly` with **polygons** (first-class). |
| `payment:sms` / `sms_prefix` | Timed `paymentMethods[].sms.number` / `.prefix` (omitted when only daily SMS exists — no null stub) |
| `maxstay` / `cooldown_period` | `rules` + SMS max/cooldown |
| `operator` + `contact:*` | `operators[]` + `zone.operatorId` |
| `fine` / `fine:discount` | `fines[]` when parseable |

Money is always `{ amount, currencyId }`. Default currency: `rsd` (RS), `eur` (ME).

Coverage policies / `coversZoneIds` are **not** seeded on import (leave absent until back office).

## Manual fill / known gaps

| Item | Why |
| --- | --- |
| `sms.prefix` on most RS zones | Not present in Serbia GeoJSON (empty string) |
| SMS `sendWindow` (e.g. Belgrade 4th slot) | Not in GeoJSON — slots get `sendWindow: null` |
| City `cases` / preposition | Not in GeoJSON |
| `workingDayOverrides` | Not in GeoJSON |
| Seasonal `fee:conditional` date ranges (`Jun 10-Sep 10`) | Not mapped to weekly windows yet |
| `coversZoneIds` / resident permits | Intentionally absent until back office |
| `holidays[]`, `holidayPolicy`, `closures[]`, `pricing.byDay`, `free_initial_minutes` | Catalog / zone fields — fill in Studio after import |

## Next step: publish as manifest + cities

The GeoJSON import writes a **monolith**. For production CDN delivery, split it:

```bash
python3 scripts/split_parking_config.py \
  -i ~/Downloads/parking-config.from-geojson.json \
  -o ~/Downloads/parking-config-delivery \
  --force-update-cities city-beograd
```

That emits `manifest.json`, `shared.json`, and `cities/{cityId}.json`.
Keep the full delivery folder **local** (or private CDN) — do not commit full
city polygon dumps to this public repo. Checked-in stub only:
[`examples/delivery/`](../examples/delivery/).

`forceUpdate` rules and layout: [delivery-manifest.md](delivery-manifest.md).

Schema: [parking-config.schema.json](parking-config.schema.json).  
Legacy production transform (different source): `scripts/transform.py`.
