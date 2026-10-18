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
| `polygon_id` + geometry ring | `polygons[]` (`enabled: true`, coords @ 6 dp) |
| `fee:conditional` | `zones[].paymentWindows` (`HH:mm`) |
| `base_rate` / `base_unit` | timed `products[].price` + `pricing` |
| `extension_rate(_2)` / `extension_unit(_2)` / `special_extension_*` | `pricing.ladder[]` (`stepIndex`, `durationMinutes`, `price`) |
| `daily_rate` + `payment:sms:daily` | `products` `kind: full_day` |
| `payment:sms` / `sms_prefix` | `paymentMethods[].sms.number` / `.prefix` |
| `maxstay` / `cooldown_period` | `rules` + SMS max/cooldown |
| `operator` + `contact:*` | `operators[]` + `zone.operatorId` |
| `fine` / `fine:discount` | `fines[]` when parseable |

Money is always `{ amount, currencyId }`. Default currency: `rsd` (RS), `eur` (ME).

Coverage policy design is unchanged: per-city `offer_highest_rank`, rank from
timed price, `coversZoneIds: []`.

## Manual fill / known gaps

| Item | Why |
| --- | --- |
| `sms.prefix` on most RS zones | Not present in Serbia GeoJSON (empty string) |
| SMS `sendWindow` (e.g. Belgrade 4th slot) | Not in GeoJSON — slots get `sendWindow: null` |
| City `cases` / preposition | Not in GeoJSON |
| `workingDayOverrides` | Not in GeoJSON |
| Temporary lots without SMS/price | Zone + disabled SMS hook; fill numbers/prices later |
| `coversZoneIds` / resident permits | Intentionally empty until back office |

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
