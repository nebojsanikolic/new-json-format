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
  shared.json            # client, locales, currencies, countries, operators, country holidays
  exchange-rates.json    # FX vs base currency (not inside currencies[] / cities)
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
| `schemaVersion` | string | **Delivery/schema envelope** version (currently `"1.0.0"`). Separate from `mainVersion`, city `version`, shared `version`, and monolith `dataVersion`. |
| `minAppVersions` | object | Per-platform floors: `{ "ios", "android", "web" }` (string or `null`). Raise a platform when that app needs a new engine capability. |
| `mainVersion` | string | Revision of this **publish** (content stamp; often mirrors monolith `dataVersion`). |
| `forceUpdate` | boolean | **Main / global** force flag (see semantics below). |
| `updateDescription` | string \| locale map | Optional whole-delivery notice. Locale map must include **all four** keys: `sr-Latn`, `sr-Cyrl`, `en`, `ru`. |
| `generatedAt` | string | ISO-8601 UTC when this delivery was built. |
| `shared` | object | Pointer to `shared.json` (see below). |
| `exchangeRates` | object | Pointer to `exchange-rates.json` (version, url, checksum, forceUpdate, …). |
| `countries` | array | Country **index** for the app (see below). Full country objects stay in `shared.json` (v1). |
| `cities` | array | One entry per city file (see below). |
| `source` | object | Optional provenance copied from the monolith. |
| `forcedExport` | object | Optional studio stamp when exported despite Validate errors (`at`, `errorCount`). |

### Integrity: `checksum` / `contentHash`

Studio and `split_parking_config.py` hash the **exact UTF-8 JSON bytes** written for `shared.json`, `exchange-rates.json`, and each `cities/{id}.json`.

| Field | Format | Meaning |
| --- | --- | --- |
| `checksum` | `sha256:<hex>` | Required on export for shared, exchange-rates, + every city entry. |
| `contentHash` | `sha256:<hex>` | Same digest as `checksum` — etag-equivalent next to `version`. |

CDN HTTP `ETag` headers and HMAC signing are **backend/ops** concerns (not written by the studio). Clients may treat `contentHash` like an etag when verifying downloads.

### Shared entry

| Field | Type | Meaning |
| --- | --- | --- |
| `version` | string | Shared catalog revision. |
| `forceUpdate` | boolean | Hard vs soft shared refresh. |
| `url` | string | Relative path (`shared.json`). |
| `checksum` / `contentHash` | string | `sha256:<hex>` of `shared.json` bytes. |
| `updateDescription` | string \| locale map | Optional “what’s new” for shared. |
| `updatedAt` | string | Optional ISO-8601 UTC. |

### Country entry (index)

v1 keeps heavy country data (and optional `coveragePolygon`) inside **`shared.json`**. The manifest still lists every country so the app can show a country list and decide updates without parsing shared first.

| Field | Type | Meaning |
| --- | --- | --- |
| `countryId` | string | Stable id (`rs`, `me`, …). |
| `timezone` | string | IANA timezone (also on the full country in shared). |
| `locales` | LocalesMap | Display names — all four keys (`sr-Latn` / `sr-Cyrl` / `en` / `ru`). |
| `version` | string | Content stamp. **v1: same as `shared.version`** (countries change with shared). |
| `forceUpdate` | boolean | **v1: same as `shared.forceUpdate`**. |
| `url` | string | Where full objects live. **v1: always `shared.json`**. Future: `countries/{id}.json` if split. |
| `checksum` / `contentHash` | string | When `url` is `shared.json`, same digest as the shared entry. |
| `updateDescription` | string \| locale map | Optional “what’s new” for that country. |
| `updatedAt` | string | Optional ISO-8601 UTC. |

### City entry

| Field | Type | Meaning |
| --- | --- | --- |
| `cityId` | string | Stable id (`city-beograd`). |
| `countryId` | string | Country id (`rs`, `me`, …). |
| `version` | string | City file revision. **Bump on any content change** for that city. |
| `forceUpdate` | boolean | Hard vs soft update for this city (see below). |
| `updateDescription` | string \| locale map | When a map, all four locale keys required. |
| `updatedAt` | string | Optional ISO-8601 UTC. |
| `url` | string | Relative path, e.g. `cities/city-beograd.json`. |
| `checksum` / `contentHash` | string | `sha256:<hex>` of the city file bytes. |

Example:

```json
{
  "schemaVersion": "1.0.0",
  "minAppVersions": { "ios": "5.0.0", "android": "5.0.0", "web": null },
  "mainVersion": "1.0.0-geojson",
  "forceUpdate": false,
  "updateDescription": {
    "en": "Schema unchanged — city price updates only.",
    "sr-Latn": "Šema nepromenjena — samo cene po gradovima.",
    "sr-Cyrl": "Шема непромењена — само цене по градовима.",
    "ru": "Схема без изменений — только цены по городам."
  },
  "shared": {
    "version": "2026.10.18.1",
    "forceUpdate": false,
    "url": "shared.json",
    "checksum": "sha256:c850e16b6589f2535c6dcebb1f1c7346286b72763408acfade37a28d3a05eb16",
    "contentHash": "sha256:c850e16b6589f2535c6dcebb1f1c7346286b72763408acfade37a28d3a05eb16"
  },
  "exchangeRates": {
    "version": "2026.10.24.1",
    "forceUpdate": false,
    "url": "exchange-rates.json",
    "checksum": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "contentHash": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  },
  "countries": [
    {
      "countryId": "rs",
      "timezone": "Europe/Belgrade",
      "locales": {
        "sr-Latn": { "name": "Srbija" },
        "sr-Cyrl": { "name": "Србија" },
        "en": { "name": "Serbia" },
        "ru": { "name": "Сербия" }
      },
      "version": "2026.10.18.1",
      "forceUpdate": false,
      "url": "shared.json",
      "checksum": "sha256:c850e16b6589f2535c6dcebb1f1c7346286b72763408acfade37a28d3a05eb16",
      "contentHash": "sha256:c850e16b6589f2535c6dcebb1f1c7346286b72763408acfade37a28d3a05eb16"
    }
  ],
  "cities": [
    {
      "cityId": "city-beograd",
      "countryId": "rs",
      "version": "2026.10.18.1",
      "forceUpdate": true,
      "url": "cities/city-beograd.json",
      "checksum": "sha256:e0f0a24b0b6465de5721a7eb8e6c13712ed3ce0201fec69018a3da7234297c5d",
      "contentHash": "sha256:e0f0a24b0b6465de5721a7eb8e6c13712ed3ce0201fec69018a3da7234297c5d"
    }
  ]
}
```

Machine schema: [`delivery-manifest.schema.json`](delivery-manifest.schema.json).  
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
| **`true`** | Schema or **global** rules require a full refresh of shared + relevant cities, and/or an **app gate** via `minAppVersions` (user must update the app if that platform is below). Treat as “do not run on stale delivery.” |
| **`false`** | Normal incremental path: compare versions and update only what changed. |

---

## When to bump versions and set `forceUpdate`

| Change type | Bump city `version`? | Set city `forceUpdate`? |
| --- | --- | --- |
| SMS number, prefix, slots, price, payment windows, products, rules that affect what the user pays or sends | **Yes** | **`true`** |
| Fine amounts / payment-related operator contact used at pay time | **Yes** | **`true`** (if old values would mislead payment) |
| Zone `enabled` flipped (hide/show parking) | **Yes** | Prefer **`true`** if leaving it soft would show illegal/outdated availability |
| Polygon geometry only (map shape), cosmetic colors, copy tweaks with no price/rule impact | **Yes** | **`false`** OK (soft / background) |
| Shared catalog only (new locale, currency metadata) | Bump **`shared.version`** | `shared.forceUpdate` as needed; city versions unchanged |
| FX rates only | Bump **`exchangeRates.version`** | `exchangeRates.forceUpdate` as needed; cities unchanged |

**Guideline:** if serving the previous city JSON could cause a wrong SMS, wrong price, wrong max stay, or illegal parking advice → **`forceUpdate: true`**. If it is map polish or non-binding copy → leave **`false`**.

Always bump the city `version` string on **any** city content change so soft updates still detect freshness. Suggested stamp: `YYYY.MM.DD.N` (e.g. `2026.10.18.1`).

---

## `exchange-rates.json`

FX is **not** stored on `currencies[]` or in city/zone payloads. Clients fetch this file when the manifest `exchangeRates` entry changes.

| Field | Type | Meaning |
| --- | --- | --- |
| `schemaVersion` | string | Envelope version |
| `version` | string | Content stamp |
| `baseCurrencyId` | string | Currency id rates are quoted against (e.g. `rsd`) |
| `asOf` | string | ISO-8601 UTC observation / publish time |
| `rates` | object | Map of `currencyId` → number (base itself is typically `1`) |
| `notes` | string \| null | Optional |

```json
{
  "schemaVersion": "1.0.0",
  "version": "2026.10.24.1",
  "baseCurrencyId": "rsd",
  "asOf": "2026-10-24T12:00:00Z",
  "rates": { "rsd": 1, "eur": 117.0 },
  "notes": null
}
```

### `exchangeRates` manifest entry

Same shape as shared: `version`, `forceUpdate`, `url` (`exchange-rates.json`), `checksum` / `contentHash`, optional `updateDescription` / `updatedAt`.

---

## `shared.json`

Rarely changing catalog:

- `client` — `{ supportedLocales, localeFallback }` (always set by split/export)
- `locales`, `currencies`, `countries`, `operators`
- `holidays` — country-scoped only (no `cityId`)
- Plus `schemaVersion`, `version`, `generatedAt`

Operators live here (not duplicated in every city file). City zones still reference `operatorId`.

```json
"client": {
  "supportedLocales": ["sr-Latn", "sr-Cyrl", "en", "ru"],
  "localeFallback": ["sr-Latn", "en", "sr-Cyrl", "ru"]
}
```

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
| `holidays` | City/municipal holidays (`cityId` set). Country holidays stay in `shared.json`. |

Payment methods and rules are **included by reference** from the city’s zones/products (not the entire global arrays).

---

## Client fetch sketch

1. GET `manifest.json`.
2. If this platform’s `minAppVersions.{ios|android|web}` is a string and app &lt; that → prompt update / gate (`null` = not gated).
3. If `forceUpdate` (main) → refresh shared + rates + all cities needed for the user’s context before use.
4. Use `manifest.countries[]` for the country list / timezone labels; compare `countries[].version` / `forceUpdate` (v1 mirrors shared) → fetch `shared.json` when shared (or any country pointing at it) needs refresh.
5. Compare `shared.version` (and `shared.forceUpdate`) → fetch `shared.json` if needed.
6. Compare `exchangeRates.version` / `forceUpdate` → fetch `exchange-rates.json` if needed.
7. For each city the user may use: if local version ≠ manifest version, or `forceUpdate`, fetch that city URL (blocking when forced).
8. Verify `checksum` (`sha256:<hex>`) against the downloaded file bytes (prefer `checksum` over `contentHash`).

---

## Script flags

| Flag | Purpose |
| --- | --- |
| `--force-update-main` | Set root `forceUpdate` |
| `--force-update-shared` | Set `shared.forceUpdate` |
| `--force-update-rates` | Set `exchangeRates.forceUpdate` |
| `--rates-version …` | Stamp `exchange-rates.json` version |
| `--force-update-cities city-a,city-b` | Hard-refresh listed cities |
| `--force-update-all-cities` | Hard-refresh every city (cutover) |
| `--city-version 2026.10.18.2` | Stamp all city files |
| `--no-checksum` | Omit `checksum` / `contentHash` on shared + city entries |
| `--compact` | Minified JSON |

See also: [geojson-import.md](geojson-import.md) · [field-reference.md](field-reference.md) · example [`examples/delivery/`](../examples/delivery/).
