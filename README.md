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
| Resolve offer (algorithm) | [`docs/client-resolve.md`](docs/client-resolve.md) |
| Precedence cheat sheet | [`docs/evaluation-order.md`](docs/evaluation-order.md) |
| Closed string enums | [`docs/enums.md`](docs/enums.md) |
| CDN / `forceUpdate` / checksums | [`docs/delivery-manifest.md`](docs/delivery-manifest.md) |
| Concepts (layers, inheritance) | [`docs/schema.md`](docs/schema.md) |
| Machine schema | [`docs/parking-config.schema.json`](docs/parking-config.schema.json) |
| GeoJSON → config (local, confidential) | [`docs/geojson-import.md`](docs/geojson-import.md) |
| Tiny delivery stub | [`examples/delivery/`](examples/delivery/) |
| Client-resolve fixtures | [`examples/client-resolve/`](examples/client-resolve/) |
| Readable city excerpt | [`examples/belgrade-snippet.json`](examples/belgrade-snippet.json) |
| Open questions (before ship) | [§ Open questions](#open-questions-before-ship) |

---

## Shape (sketch)

```
catalog      countries · cities · operators · currencies · locales · holidays
geography    zones → polygons     (polygon.overrides.* wins over zone)
commerce     products · paymentMethods · rules
```

Holidays, closures, `pricing.byDay`, and `free_initial_minutes`: [docs/holidays-and-time-rules.md](docs/holidays-and-time-rules.md).  
Full runtime precedence: [docs/evaluation-order.md](docs/evaluation-order.md).  
Closed string enums (Swift/Kotlin): [docs/enums.md](docs/enums.md).  
`shared.client` locales + fallback: see field-reference / enums. Stable optional fields prefer explicit `null` over omit.

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

Also: hours as `"HH:mm"` / `"24:00"` · locales as complete maps (`sr-Latn`/`sr-Cyrl`/`en`/`ru` — all four required) · envelope `schemaVersion` separate from `mainVersion` / city / shared content versions.

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

## Open questions (before ship)

Decisions still open before production cutover — not a backlog dump. No new schema fields until these land.

- **Residential subzones / “don’t nag to pay”** — In Belgrade (and similar), some areas are residential subzones. Users with a residential ticket get notifications when they enter that zone, but they shouldn’t need to buy on-street parking there. Open: how should data + app treat this? (polygon with `residents` eligibility vs separate zone vs future `purchaseLocation` / suppress pay prompts when an active resident permit covers the area.) **Do not implement a field yet** — product + app decision first. Related: [enums.md](docs/enums.md) (`EligibilityType`) · [evaluation-order.md](docs/evaluation-order.md) · [holidays-and-time-rules.md](docs/holidays-and-time-rules.md) (domain: public on-street).
- **Dev / prod distribution rail + CI validate gate** — Studio publish → separate dev/prod destinations; CI re-Validates + checks checksums on push (block on failure). Encrypt/sign later. Ops plan lives outside this schema repo.
- **Signed manifest / CDN encryption** — Deferred; needed for hardened prod delivery, not blocking format freeze.
- **`checksum` vs `contentHash`** — Both currently carry the same `sha256:<hex>` digest ([delivery-manifest.md](docs/delivery-manifest.md)). Prefer **`checksum`** as the one clients verify; keep or drop `contentHash` once apps agree.
- **Coverage `coversZoneIds` + SMS `sendWindow`** — Schema ready; fill in studio where business needs them (not seeded on GeoJSON import).
- **Client-resolve fixtures vs real Belgrade residential** — Optional follow-up golden case once the residential-subzone model is decided ([examples/client-resolve/](examples/client-resolve/)).

## Status notes

- Cutover from `zonesData_v2` is one-time (force-update OK).
- Night rates, seasonal overlays, webview card, etc. may stay empty until back office fills them — see [field-reference.md](docs/field-reference.md).
- Full polygons are confidential; only truncated samples ship in examples.
