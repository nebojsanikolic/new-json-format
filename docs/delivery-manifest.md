# Delivery: manifest + shared + per-city files

Production clients **do not** download the full monolith on every launch.
They fetch a small **`manifest.json`**, then refresh **`shared.json`** and only
the **city files** that changed (or that require a forced refresh).

The monolith (`parking-config.*.json`) remains valid for tools, transforms, and
back-office exports. Publish step:

```bash
python3 scripts/split_parking_config.py \
  -i ~/Downloads/parking-config.from-geojson.json \
  -o ~/Downloads/parking-config-delivery \
  --force-update-cities city-beograd
```

## Layout

```
delivery/
  manifest.json          # always fetched first (small)
  shared.json            # locales, currencies, countries, operators
  cities/
    city-beograd.json
    city-podgorica.json
    …
```

Relative `url` values in the manifest are resolved against the same CDN/base
path as `manifest.json` (e.g. `https://cdn.example/parking/v1/`).

---

## `manifest.json`

| Field | Type | Meaning |
| --- | --- | --- |
| `schemaVersion` | string | Delivery envelope version (currently `"1.0.0"`). |
| `minAppVersion` | string | App must be ≥ this to consume this delivery. Raise when the engine needs a new capability. |
| `mainVersion` | string | Revision of this publish (often mirrors monolith `dataVersion`). |
| `forceUpdate` | boolean | **Main / global** force flag (see semantics below). |
| `generatedAt` | string | ISO-8601 UTC when this delivery was built. |
| `shared` | object | Pointer to `shared.json` (`version`, `forceUpdate`, `url`). |
| `cities` | array | One entry per city file (see below). |
| `source` | object | Optional provenance copied from the monolith. |

### City entry

| Field | Type | Meaning |
| --- | --- | --- |
| `cityId` | string | Stable id (`city-beograd`). |
| `countryId` | string | Country id (`rs`, `me`, …). |
| `version` | string | City file revision. **Bump on any content change** for that city. |
| `forceUpdate` | boolean | Hard vs soft update for this city (see below). |
| `url` | string | Relative path, e.g. `cities/city-beograd.json`. |
| `checksum` | string | Optional SHA-256 hex of the city file bytes (integrity). |

Example:

```json
{
  "schemaVersion": "1.0.0",
  "minAppVersion": "5.0.0",
  "mainVersion": "1.0.0-geojson",
  "forceUpdate": false,
  "shared": {
    "version": "2026.10.18.1",
    "forceUpdate": false,
    "url": "shared.json"
  },
  "cities": [
    {
      "cityId": "city-beograd",
      "countryId": "rs",
      "version": "2026.10.18.1",
      "forceUpdate": true,
      "url": "cities/city-beograd.json",
      "checksum": "optional-sha256"
    }
  ]
}
```

Tiny checked-in sample: [`examples/delivery/`](../examples/delivery/).

---

## `forceUpdate` semantics

### City (`cities[].forceUpdate`)

| Value | Client behavior |
| --- | --- |
| **`true`** | **Hard refresh.** Download this city file **before** relying on it for parking in that city. Do **not** keep serving a stale cached city slice (e.g. after SMS price / payment / rule changes that would make old data wrong or illegal). Block or defer city-specific parking UX until the new file is on disk. |
| **`false`** | **Soft update.** Cached city data may still be used. Refresh in the background when convenient; swap in when ready. |

### Shared (`shared.forceUpdate`)

| Value | Client behavior |
| --- | --- |
| **`true`** | Refresh `shared.json` before trusting catalog fields that affect display or payment currency/country setup. |
| **`false`** | Soft refresh of locales / currencies / countries / operators. |

### Main (`manifest.forceUpdate`)

| Value | Client behavior |
| --- | --- |
| **`true`** | Schema or **global** rules require a full refresh of shared + relevant cities, and/or an **app gate** via `minAppVersion` (user must update the app if below). Treat as “do not run on stale delivery.” |
| **`false`** | Normal incremental path: compare versions and update only what changed. |

---

## When to bump versions and set `forceUpdate`

| Change type | Bump city `version`? | Set city `forceUpdate`? |
| --- | --- | --- |
| SMS number, prefix, slots, price, payment windows, products, rules that affect what the user pays or sends | **Yes** | **`true`** |
| Fine amounts / payment-related operator contact used at pay time | **Yes** | **`true`** (if old values would mislead payment) |
| Zone `enabled` flipped (hide/show parking) | **Yes** | Prefer **`true`** if leaving it soft would show illegal/outdated availability |
| Polygon geometry only (map shape), cosmetic colors, copy tweaks with no price/rule impact | **Yes** | **`false`** OK (soft / background) |
| Shared catalog only (new locale, currency rate) | Bump **`shared.version`** | `shared.forceUpdate` as needed; city versions unchanged |

**Guideline:** if serving the previous city JSON could cause a wrong SMS, wrong price, wrong max stay, or illegal parking advice → **`forceUpdate: true`**. If it is map polish or non-binding copy → leave **`false`**.

Always bump the city `version` string on **any** city content change so soft updates still detect freshness. Suggested stamp: `YYYY.MM.DD.N` (e.g. `2026.10.18.1`).

---

## `shared.json`

Rarely changing catalog:

- `locales`, `currencies`, `countries`, `operators`
- Plus `schemaVersion`, `version`, `generatedAt`

Operators live here (not duplicated in every city file). City zones still reference `operatorId`.

---

## `cities/{cityId}.json`

One city slice:

| Field | Meaning |
| --- | --- |
| `cityId`, `countryId`, `version` | Identity + revision (also mirrored in the manifest entry). |
| `city` | The city catalog record. |
| `zones`, `polygons` | Geography for this city. |
| `products`, `paymentMethods`, `rules` | Commerce referenced by this city’s zones/products. |
| `coveragePolicies`, `residentPermits`, `fines` | City-scoped policy / extras. |

Payment methods and rules are **included by reference** from the city’s zones/products (not the entire global arrays).

---

## Client fetch sketch

1. GET `manifest.json`.
2. If `minAppVersion` > app → prompt update / gate.
3. If `forceUpdate` (main) → refresh shared + all cities needed for the user’s context before use.
4. Compare `shared.version` (and `shared.forceUpdate`) → fetch `shared.json` if needed.
5. For each city the user may use: if local version ≠ manifest version, or `forceUpdate`, fetch that city URL (blocking when forced).
6. Optionally verify `checksum`.

---

## Script flags

| Flag | Purpose |
| --- | --- |
| `--force-update-main` | Set root `forceUpdate` |
| `--force-update-shared` | Set `shared.forceUpdate` |
| `--force-update-cities city-a,city-b` | Hard-refresh listed cities |
| `--force-update-all-cities` | Hard-refresh every city (cutover) |
| `--city-version 2026.10.18.2` | Stamp all city files |
| `--no-checksum` | Omit SHA-256 on entries |
| `--compact` | Minified JSON |

See also: [geojson-import.md](geojson-import.md) · [field-reference.md](field-reference.md) · example [`examples/delivery/`](../examples/delivery/).
