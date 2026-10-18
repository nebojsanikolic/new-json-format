# Parking config — new rule-data format

Human-readable **concept** guide to `parking-config.generated.json`.

| Doc | Role |
| --- | --- |
| [**field-reference.md**](field-reference.md) | **Every field** — type, required/optional, meaning, examples |
| [parking-config.schema.json](parking-config.schema.json) | Machine JSON Schema |
| This file | Layers, inheritance, versioning, production mapping |

## Quick path for reviewers

1. Skim **Layers** / **Money** / **Locales** below.
2. Use [field-reference.md](field-reference.md) when checking a specific property.
3. Open [`../examples/belgrade-snippet.json`](../examples/belgrade-snippet.json) for a concrete city.
4. Full data: [`../data/parking-config.generated.json`](../data/parking-config.generated.json).
5. Mapping from production: bottom of this doc (**Production → new mapping**).

## Why this shape

- **Cutover, not compat** — no legacy field names; apps that need this format force-update once.
- **Rule-data** — new rule *kinds* can appear later; apps ignore unknown `type` values and keep selling what they understand.
- **Back-office first** — clear names (`paymentWindows`, `messageSlots`, `currencyId`), locales as maps, money always structured.
- **Channel-agnostic payment** — products say *what* is sold; `paymentMethods[]` say *how* (SMS today, `webview_card` later) without reshaping zones or products.

## Top level

| Field | Role |
| --- | --- |
| `dataVersion` | Monotonic config version for cache / “is newer?” |
| `minAppVersion` | App must be ≥ this to consume the file |
| `generatedAt` | ISO timestamp of generation |
| `source` | Provenance of the transform (URL + legacy version) |
| `locales` | Supported UI languages + default sort order |
| `currencies` | Catalog with exchange rates |
| `countries` | Catalog + required timezone |
| `operators` | Fine / operator catalog (empty until back office fills) |
| `cities` | Catalog + center, timezone, zone refs |
| `zones` | Geography layer: hours, color, products, payment methods |
| `polygons` | Rings under a zone; **overrides beat zone** when set |
| `products` | What is sold (timed / full-day / …) |
| `paymentMethods` | How to pay (`sms`, `webview_card`, …) |
| `rules` | Typed rule objects referenced by id |
| `coveragePolicies` | Multi-zone overlap + expensive-covers-cheaper |
| `residentPermits` | Permit → valid zones (hooks; empty from prod) |
| `fines` | Fine amounts / discounts (hooks; empty from prod) |

## Layers

```
catalog          countries · cities · operators · currencies · locales
geography        zones → polygons   (polygon.overrides.* wins over zone)
commerce         products + rules + paymentMethods   (linked by id)
```

### Inheritance

Any value present under `polygon.overrides` replaces the same field on the parent zone for that polygon only (hours, prices via product refs, payment methods, color, eligibility, etc.).

### Money

Everywhere money appears:

```json
{ "amount": 80.0, "currencyId": "rsd" }
```

Never a bare number with a sibling currency string. Decimals are explicit. Exchange rates live on the currency catalog (vs a base currency; production used RSD as base).

### Locales

Maps keyed by locale id (`sr-Latn`, `sr-Cyrl`, `en`, `ru`), not parallel `name_en` fields. Grammatical cases nest under the locale:

```json
"locales": {
  "sr-Latn": {
    "name": "Beograd",
    "preposition": "u",
    "cases": {
      "genitive": "Beograda",
      "dative": "Beogradu",
      "accusative": "Beograd",
      "locative": "Beogradu",
      "instrumental": "Beogradom"
    },
    "alternativeNames": []
  },
  "en": { "name": "Belgrade" }
}
```

### Effective dating

Optional `effectiveFrom` / `effectiveTo` (ISO date or datetime) on zones, polygons, products, payment methods, prices, and seasonal windows. Null / omitted = always active. Back office can stage future prices and polygons ahead of time.

### Versioning & unknown rules

- Bump `dataVersion` on every publish.
- Raise `minAppVersion` only when the *engine* must understand a new capability to stay safe.
- Rule / payment `type` strings unknown to an older app: ignore that rule or hide that payment path; keep offering known ones.

## Countries & cities

- `timezone` **required** (IANA), on country and overridable on city.
- Countries derived from production lists: Serbia (`cities`) and Montenegro (`montenegro_cities`).
- Optional `coveragePolygon` for country/city map framing (not present in production → null).
- `languageSortOrder` — preferred locale ids for display sorting.

## Zones

Back-office fields include:

- `enabled` — required boolean; `false` = hide zone in the app
- `color`, multilingual `locales` (name, description, `infoNote`)
- `paymentWindows[]` — split windows per weekday set; times as `HH:mm`
- `workingDayOverrides[]` — calendar dates that use weekday hours (from legacy `working_days_override`)
- `productIds`, `paymentMethodIds`, `polygonIds` — **id references** into top-level `products` / `paymentMethods` / `polygons` (not nested objects): products = what you buy, payment methods = how you pay
- `eligibility` — `{ "type": "public" }` or `{ "type": "residents", ... }` hooks
- `fullDayOnly` — zone only sells full-day products (still has color, cards, polygons)
- `seasonalWindows[]` — active date ranges for seasonal / event zones

Hours use **`HH:mm` strings** (`"07:00"`, `"22:00"`). Use `"24:00"` for end-of-day midnight. Closed day = empty windows for that day set (legacy `start`/`end` null).

Zones (and polygons) have **`enabled`**. When `false`, the app must hide them. Production transform sets `enabled: true` for all.

Coordinates (city centers, polygon rings) are **rounded to 6 decimal places**.

## Polygons

```json
{
  "id": "poly-…",
  "zoneId": "zone-…",
  "enabled": true,
  "ring": [{ "latitude": 44.814512, "longitude": 20.456590 }],
  "overrides": {},
  "effectiveFrom": null,
  "effectiveTo": null
}
```

`overrides` may repeat any zone-level commercial/geo field. Empty object = inherit everything from the zone.

## Products

| `kind` | Meaning |
| --- | --- |
| `timed` | Duration-based parking (hourly / per-minute / ladder) |
| `full_day` | Daily ticket |
| `permit` | Resident / other permit product (hook) |

Important fields:

- `price` — structured money (list / base price)
- `pricing.mode` — `per_hour` | `per_minute` | `fixed` | `ladder`
- `pricing.baseDurationMinutes` — minutes granted by one purchase unit (from legacy `value`)
- `pricing.ladder[]` — nth-hour prices when differing
- `pricing.nightRates[]` — night windows + prices
- `pricing.seasonalPrices[]` — summer/winter etc.
- `validity.mode` — for full-day: `calendar_day` | `rolling_24h`
- `validity.buttonColor` — full-day button color
- `coversZoneIds` — this ticket also covers listed cheaper zones
- `paymentMethodIds` — which payment channels can buy this product
- `ruleIds` — attached typed rules
- `eligibility` — who may buy

## Payment methods (channel-agnostic)

### `sms` (production)

```json
{
  "id": "pay-sms-…",
  "type": "sms",
  "enabled": true,
  "sms": {
    "number": "9111",
    "prefix": "",
    "messageSlots": [
      {
        "index": 1,
        "durationMinutes": 60,
        "sendWindow": null
      },
      {
        "index": 2,
        "durationMinutes": 30,
        "sendWindow": {
          "relativeToSlotIndex": 1,
          "fromMinutesBeforeEnd": 10,
          "toMinutesBeforeEnd": 0
        }
      }
    ],
    "maxDurationMinutes": 90,
    "cooldownAfterMax": { "enabled": true, "resumeNextPaymentWindow": true }
  }
}
```

- **messageSlots** — nth SMS duration + optional send window (Belgrade 4th-in-last-10-min pattern).
- Production usually yields a **single** slot from `value` (minutes) and `maxDurationMinutes` from `restriction_time` when `restriction` is true.
- Belgrade multi-slot rules that were hard-coded in the app are **not** fully present in production JSON; the structure is ready for back office to add them.

### `webview_card` (future — no reshape)

```json
{
  "id": "pay-webview-example",
  "type": "webview_card",
  "enabled": false,
  "webviewCard": {
    "urlTemplate": "https://pay.example.com/checkout?zone={zoneId}&product={productId}&plate={plate}",
    "returnUrlScheme": "parkingapp://payment-result",
    "parameters": {}
  }
}
```

Add a method + app support for the type. Do **not** change product or zone shape.

## Rules

Typed objects; apps skip unknown `type`:

| `type` | Purpose |
| --- | --- |
| `max_duration` | Cap cumulative paid minutes |
| `cooldown_after_max` | Block further payments after max until next window |
| `sms_slot_send_window` | Restrict when slot N may be sent |
| `resident_only` | Eligibility shorthand |
| `seasonal_active` | Zone/product only active in windows |

## Coverage / overlap policy

One policy model per city (or subset):

```json
{
  "id": "coverage-beograd",
  "cityId": "city-beograd",
  "onOverlap": "offer_highest_rank",
  "zones": [
    {
      "zoneId": "zone-beograd-zona-a",
      "rank": 600,
      "coversZoneIds": ["zone-beograd-zona-1", "zone-beograd-zona-2"]
    }
  ]
}
```

`onOverlap`: `offer_highest_rank` | `offer_all` | `offer_none`.  
`coversZoneIds` implements “expensive ticket covers cheaper zones.” Production did not encode coverage graphs explicitly — generated ranks follow zone price; covers lists are left empty unless inferred later in back office.

## Residents, fines, operators

- `eligibility.type`: `public` | `residents` | future hooks (`vehicle_class`, …).
- `residentPermits[]` — permit id, holder rules, `validZoneIds`.
- `operators[]` / `fines[]` — centralized fine display, discount amount or %, discount period duration.

Production has no resident/fine/operator records → arrays are empty shells so the back office can fill them without a format change.

## IDs

Fresh stable string ids (`city-beograd`, `zone-beograd-zona-1`, `rsd`, …). Optional `legacyId` keeps old numeric ids for review / one-time migration tooling. No requirement to preserve numbers forever.

## Production → new mapping (summary)

| Legacy | New |
| --- | --- |
| `version` | `source.legacyVersion`; new `dataVersion` starts at `1.0.0` |
| `currency[]` | `currencies[]` with string ids + locale name map |
| `cities` / `montenegro_cities` | `countries` rs/me + `cities[]` |
| city name_* / cases | `city.locales` |
| `Zones[]` | `zones[]` + `polygons[]` + timed `products[]` + `paymentMethods` sms |
| `parking_hours` | `paymentWindows[]` |
| `value` | `pricing.baseDurationMinutes` + sms `messageSlots[0].durationMinutes` |
| `restriction` / `restriction_time` | `max_duration` rule + sms `maxDurationMinutes` |
| `daily_tickets[]` | `products` with `kind: full_day` |
| `sms_number` / `sms_prefix` / `sms_prefix_daily` | payment method `sms` |
| `forZones` | `product.zoneIds` |
| `working_days_override` | `workingDayOverrides` |
| `info_note` | `locales.*.infoNote` |

## What production cannot fill

Documented in schema, empty or example-disabled in data:

- Night rates, per-hour ladders beyond flat price, per-minute mode instances
- Seasonal / event overlays, seasonal pricing schedules
- Multi-slot SMS send windows (Belgrade 4th SMS rule)
- Explicit coverage graphs / multi-zone UX beyond price-ranked stubs
- Webview card methods (one disabled example object may be included)
- Resident permits, fines, operators, country/city coverage polygons
- Split payment windows beyond weekday/saturday/sunday (structure supports multiple windows per day set)

## Files

| Path | Role |
| --- | --- |
| `data/parking-config.generated.json` | Full transformed config (**main deliverable**) |
| `data/zonesData_v2.source.json` | Snapshot of production input |
| `examples/belgrade-snippet.json` | Readable Belgrade excerpt without huge polygons |
| `docs/parking-config.schema.json` | JSON Schema |
| `scripts/transform.py` | Regenerator from source → generated |
