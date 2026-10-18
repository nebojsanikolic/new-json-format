# Field reference — parking config

Complete parameter list for teammates reviewing or editing the format.  
Companion docs: [schema.md](schema.md) (concepts) · [enums.md](enums.md) (closed string enums) · [parking-config.schema.json](parking-config.schema.json) (machine schema) · [../README.md](../README.md).

**Conventions used below**

| Marker | Meaning |
| --- | --- |
| **R** | Required on that object |
| **O** | Optional — **prefer explicit `null`** for known scalar/object fields on the stable shape (zone / polygon / product / payment / city / country / fine). Do not require apps to probe “does this key exist?”. Omitting is still valid for older files; validators must accept either. |
| Arrays | Empty list → `[]` (not `null`) |
| LocalesMap | Always all four keys: `sr-Latn`, `sr-Cyrl`, `en`, `ru` |
| string id | Stable back-office id (`city-beograd`, `rsd`, …) |
| locale map | Object keyed by locale id (`sr-Latn`, `sr-Cyrl`, `en`, `ru`, …) |

Do **not** invent null stubs for nested structures that are not part of that entity’s model (e.g. no fake `sms` object on a webview-only method beyond the stable `webviewCard` / channel fields).

---

## Root object (`ParkingConfig`)

| Field | Type | R/O | Meaning |
| --- | --- | --- | --- |
| `dataVersion` | string | **R** | Config revision for cache / “is this newer?”. Bump on every publish (e.g. `"1.0.0"`). |
| `minAppVersion` | string | **R** | App must be ≥ this semver-like string to load the file. Raise only when the engine must understand a new capability. |
| `generatedAt` | string \| null | O | ISO-8601 UTC timestamp when this file was generated. |
| `source` | object | O | Provenance of a transform (see below). |
| `locales` | array | **R** | Catalog of UI languages + default sort order. |
| `currencies` | array | **R** | Currency catalog (codes, symbols, exchange rates). |
| `countries` | array | **R** | Country catalog (timezone required). |
| `operators` | array | **R** | Fine / operator catalog (may be `[]`). |
| `cities` | array | **R** | City catalog. |
| `zones` | array | **R** | Parking zones. |
| `polygons` | array | **R** | Polygon rings; may override zone fields. |
| `products` | array | **R** | What is sold (timed, full-day, permit). |
| `paymentMethods` | array | **R** | How to pay (`sms`, `webview_card`, …). |
| `rules` | array | **R** | Typed rule objects referenced by id. |
| `coveragePolicies` | array | **R** | Multi-zone overlap / coverage policy. |
| `residentPermits` | array | **R** | Resident permits (may be `[]`). |
| `fines` | array | **R** | Fine amounts / discounts (may be `[]`). |
| `holidays` | array | O | Country + city/municipal holidays (omit or `[]`). |
| `client` | object | O* | Client constants (`supportedLocales`, `localeFallback`). Optional on older monoliths; **always** present on `shared.json` after split/export. |

```json
{
  "dataVersion": "1.0.0",
  "minAppVersion": "5.0.0",
  "generatedAt": "2026-10-18T09:37:00Z",
  "client": {
    "supportedLocales": ["sr-Latn", "sr-Cyrl", "en", "ru"],
    "localeFallback": ["sr-Latn", "en", "sr-Cyrl", "ru"]
  },
  "locales": [],
  "currencies": [],
  "countries": [],
  "operators": [],
  "holidays": [],
  "cities": [],
  "zones": [],
  "polygons": [],
  "products": [],
  "paymentMethods": [],
  "rules": [],
  "coveragePolicies": [],
  "residentPermits": [],
  "fines": []
}
```

### `client` (also on `shared.json`)

| Field | Type | R/O | Meaning |
| --- | --- | --- | --- |
| `supportedLocales` | string[] | **R** | Locales the UI must support (the four `LocalesMap` keys). |
| `localeFallback` | string[] | **R** | Ordered fallback when a `LocalesMap` string is empty for the UI locale. Default: `["sr-Latn","en","sr-Cyrl","ru"]`. |

See [enums.md](enums.md) · [client-resolve.md](client-resolve.md) · [evaluation-order.md](evaluation-order.md).

### `source`

| Field | Type | R/O | Meaning |
| --- | --- | --- | --- |
| `url` | string | O | URL of the production/source JSON used for transform. |
| `legacyVersion` | number \| string \| null | O | Legacy file `version` field. |
| `notes` | string | O | Free-text transform notes. |

---

## Shared types

### Money

Used **everywhere** money appears. Never a bare number with a sibling currency string.

| Field | Type | R/O | Meaning |
| --- | --- | --- | --- |
| `amount` | number | **R** | Decimal-capable amount (e.g. `80`, `0.6`, `156.5`). |
| `currencyId` | string | **R** | Id of an entry in `currencies` (e.g. `"rsd"`, `"eur"`). |

```json
{ "amount": 80.0, "currencyId": "rsd" }
```

### LatLng (`[lat, lon]`)

A point is a **2-element array**: `[latitude, longitude]` (lat-first — mobile-friendly, **not** GeoJSON’s lon-first). Both numbers **rounded to 6 decimal places**.

```json
[44.814512, 20.45659]
```

Used for `city.center`, `coveragePolygon`, and every `polygons[].ring` vertex. Do **not** use `{ "latitude", "longitude" }` objects (verbose key repetition). Always round when writing config.

### Time of day (`HH:mm`)

All clock fields (`startHour`, `endHour` on payment windows and night rates) use **strings**, not decimal numbers.

| Format | Meaning |
| --- | --- |
| `"07:00"` | 07:00 local time |
| `"14:30"` | 14:30 (half hours supported) |
| `"24:00"` | End of calendar day / midnight end (allowed for end times) |

Pattern: `HH:mm` with `00:00`–`23:59`, plus `"24:00"` for end-of-day.

```json
{ "days": ["monday"], "startHour": "07:00", "endHour": "22:00" }
```

**Do not** use decimals like `7.0` or `22.5` — use `"07:00"` / `"22:30"`.

### Effective dating

Optional on many entities. `null` / omitted = always active.

| Field | Type | R/O | Meaning |
| --- | --- | --- | --- |
| `effectiveFrom` | string \| null | O | ISO date or datetime when this record becomes active. |
| `effectiveTo` | string \| null | O | ISO date or datetime when it stops (exclusive or inclusive — app should treat as end of validity window; document in back office UX). |

Use to stage future prices, polygons, or seasonal products ahead of time.

### Locales map (`locales` on entities) — shared contract

**One decoder model** for every in-app localized object:

```ts
type LocaleId = "sr-Latn" | "sr-Cyrl" | "en" | "ru";
type LocaleStrings = {
  name?: string;
  description?: string;
  infoNote?: string;
  preposition?: string;
  alternativeNames?: string[];
  cases?: { genitive?: string; dative?: string; accusative?: string; locative?: string; instrumental?: string };
};
type LocalesMap = Record<LocaleId, LocaleStrings>; // all four keys always required
```

Swift-friendly: `[LocaleId: LocaleStrings]` with `LocaleId` limited to those four raw values.

**Illegal:** missing `sr-Cyrl` or `ru`, or only `sr-Latn`+`en`. Schema + Studio Validate reject partial maps. Extra keys (`sk`, `hu`, …) are also illegal — put aliases in `alternativeNames`.

Per-locale **fields** may differ by entity (holiday may only set `name`; zone may set `name` + `description` + `infoNote`) — but the **four locale keys are always required**.

Back-office-only labels (`seasonalWindows[].label`, `rules[].notes`, `source.notes`, `eligibility.notes`) may stay plain strings.

| Field under each locale | Type | R/O | Meaning |
| --- | --- | --- | --- |
| `name` | string | O* | Display name (*required non-empty for holidays; expected for cities/zones). |
| `description` | string | O | Longer description. |
| `infoNote` | string | O | Extra info note (e.g. zone tip). |
| `preposition` | string | O | Grammar helper for city phrases. |
| `alternativeNames` | string[] | O | Search aliases. |
| `cases` | object | O | Grammatical cases (see below). |

#### `cases` (under a locale)

| Field | Type | R/O | Meaning |
| --- | --- | --- | --- |
| `genitive` | string | O | Genitive form. |
| `dative` | string | O | Dative form. |
| `accusative` | string | O | Accusative form. |
| `locative` | string | O | Locative form. |
| `instrumental` | string | O | Instrumental form. |

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
    }
  },
  "sr-Cyrl": { "name": "Београд" },
  "en": { "name": "Belgrade" },
  "ru": { "name": "Белград" }
}
```

Used on: currencies, countries, operators, cities, zones, `polygon.overrides`, products, resident permits, fines, holidays, closure reasons.

### Eligibility

| Field | Type | R/O | Meaning |
| --- | --- | --- | --- |
| `type` | EligibilityType | **R** | Closed enum: `"public"` \| `"residents"`. See [enums.md](enums.md). |
| `notes` | string | O | Back-office note. |
| *(extra)* | any | O | Extension fields for future eligibility kinds. |

```json
{ "type": "public" }
```

```json
{ "type": "residents", "notes": "Resident permit required" }
```

---

## Catalog layer

### `locales[]` — language catalog

| Field | Type | R/O | Meaning |
| --- | --- | --- | --- |
| `id` | string | **R** | Locale id used as map keys elsewhere (`sr-Latn`, `en`, …). |
| `name` | string | O | Human label for the language in back office / settings. |
| `sortOrder` | integer | **R** | Default language sort order (lower = earlier). |

```json
{ "id": "sr-Latn", "name": "Srpski (latinica)", "sortOrder": 1 }
```

### `currencies[]`

| Field | Type | R/O | Meaning |
| --- | --- | --- | --- |
| `id` | string | **R** | Stable id (`rsd`, `eur`, …). Referenced by money objects. |
| `legacyId` | integer \| null | O | Old numeric currency id (review / tooling). |
| `code` | string | **R** | ISO-like code (`RSD`, `EUR`). |
| `symbol` | string | **R** | Display symbol (`RSD`, `€`). |
| `exchangeRate` | number | **R** | Rate vs base currency (production base = RSD). |
| `locales` | locale map | O | Localized currency name. |

```json
{
  "id": "rsd",
  "legacyId": 1,
  "code": "RSD",
  "symbol": "RSD",
  "exchangeRate": 1,
  "locales": { "en": { "name": "Serbian Dinar" } }
}
```

### `countries[]`

| Field | Type | R/O | Meaning |
| --- | --- | --- | --- |
| `id` | string | **R** | Country id (`rs`, `me`). |
| `timezone` | string | **R** | IANA timezone (`Europe/Belgrade`). **Required.** |
| `defaultCurrencyId` | string | **R** | Default currency id for cities in this country. |
| `languageSortOrder` | string[] | O | Preferred locale ids for display sorting. |
| `locales` | locale map | O | Country names. |
| `coveragePolygon` | LatLng[] \| null | O | Optional country map outline. |
| `effectiveFrom` / `effectiveTo` | string \| null | O | Effective dating. |

### `operators[]`

Centralized operators for fine display, contacts, etc. Empty until back office fills.

| Field | Type | R/O | Meaning |
| --- | --- | --- | --- |
| `id` | string | **R** | Operator id. |
| `legacyId` | integer \| null | O | Old id if any. |
| `locales` | locale map | O | Operator display name. |
| `contact` | object | O | Free-form contact info (phone, url, …). |

### `cities[]`

| Field | Type | R/O | Meaning |
| --- | --- | --- | --- |
| `id` | string | **R** | City id (`city-beograd`). |
| `legacyId` | integer \| null | O | Old `city_id`. |
| `countryId` | string | **R** | Parent country id. |
| `timezone` | string | **R** | IANA timezone (may match country; overridable per city). |
| `shortName` | string | O | Short code (`BG`). |
| `center` | LatLng | **R** | Map center. |
| `locales` | locale map | O | Names + cases + preposition. |
| `zoneIds` | string[] | O | Zones belonging to this city. |
| `coveragePolicyId` | string \| null | O | Id of this city’s coverage policy. |
| `coveragePolygon` | LatLng[] \| null | O | City parking coverage outline (optional). |
| `fullDayButtonColor` | string \| null | O | Suggested color for full-day CTA (e.g. Šabac). |
| `effectiveFrom` / `effectiveTo` | string \| null | O | Effective dating. |

### `holidays[]`

Country and city/municipal holidays. Require `countryId` and/or `cityId`. Delivery: no `cityId` → `shared.json`; with `cityId` → that city’s slice.

| Field | Type | R/O | Meaning |
| --- | --- | --- | --- |
| `id` | string | **R** | Unique holiday id. |
| `countryId` | string | O* | Country scope (*required if no `cityId`). |
| `cityId` | string | O* | Municipal scope (*required if no `countryId`; may combine with `countryId`). |
| `date` | string | **R** | `YYYY-MM-DD` in local timezone. |
| `locales` | locale map | **R** | In-app name (`locales.*.name` required non-empty). |
| `defaultBehavior` | string | **R** | `"free"` \| `"closed"` \| `"weekday"` \| `"sunday"`. |
| `notes` | string | O | Back-office only. |

```json
{
  "id": "hol-rs-2027-01-01",
  "countryId": "rs",
  "date": "2027-01-01",
  "locales": {
    "sr-Latn": { "name": "Nova godina" },
    "sr-Cyrl": { "name": "Нова година" },
    "en": { "name": "New Year's Day" },
    "ru": { "name": "Новый год" }
  },
  "defaultBehavior": "free"
}
```

---

## Geography layer

### Id references (important)

`productIds`, `paymentMethodIds`, `polygonIds`, `ruleIds`, `zoneIds`, etc. are **arrays of string ids** that point at other top-level arrays. They are **not** nested full objects.

| Field on zone / product | Points to | Meaning |
| --- | --- | --- |
| `zone.productIds` | top-level `products[]` | **What** you can buy in this zone (timed ticket, full-day, …) |
| `zone.paymentMethodIds` | top-level `paymentMethods[]` | **How** you can pay (SMS number, later webview card, …) |
| `zone.polygonIds` | top-level `polygons[]` | Map shapes for this zone |
| `product.paymentMethodIds` | top-level `paymentMethods[]` | Which payment channels can buy **this** product |
| `product.ruleIds` | top-level `rules[]` | Rules attached to the product |
| `product.zoneIds` | top-level `zones[]` | Zones the product applies to |

```json
// zone (references only)
"productIds": ["prod-timed-beograd-zona-1"],
"paymentMethodIds": ["pay-sms-beograd-zona-1"]

// resolve elsewhere in the same file
"products": [ { "id": "prod-timed-beograd-zona-1", ... } ],
"paymentMethods": [ { "id": "pay-sms-beograd-zona-1", "type": "sms", ... } ]
```

### `zones[]`

| Field | Type | R/O | Meaning |
| --- | --- | --- | --- |
| `id` | string | **R** | Zone id. |
| `legacyId` | integer \| null | O | Old zone `id`. |
| `cityId` | string | **R** | Parent city. |
| `enabled` | boolean | **R** | When `false`, the app **must not show** this zone (hidden on map and purchase UI). Production transform sets `true` for all zones. |
| `color` | string | **R** | Map / card color (hex). |
| `locales` | locale map | O | Zone name, description, `infoNote`. |
| `polygonIds` | string[] | O | Ids → `polygons[]`. |
| `productIds` | string[] | O | Ids → `products[]` (**what** can be bought). |
| `paymentMethodIds` | string[] | O | Ids → `paymentMethods[]` (**how** to pay). |
| `paymentWindows` | PaymentWindow[] | O | When collection / paid parking applies (split windows supported). Outside these windows = not collected; car may stay until the next window opens (no grace field). |
| `workingDayOverrides` | string[] | O | Calendar dates that use **weekday** windows (from legacy `working_days_override`). |
| `eligibility` | Eligibility | O | Who may park / buy here. |
| `fullDayOnly` | boolean | O | If true, zone only sells full-day products (still has color, polygons, cards). |
| `seasonalWindows` | SeasonalWindow[] | O | Active date ranges; optional polygon expansion for events. |
| `operatorId` | string \| null | O | Operator responsible for this zone. |
| `holidayPolicy` | HolidayPolicy | O | Observe / dismiss / override catalog holidays. |
| `closures` | Closure[] | O | Temporary zone-wide closures. |
| `effectiveFrom` / `effectiveTo` | string \| null | O | Effective dating. |

#### `holidayPolicy`

| Field | Type | R/O | Meaning |
| --- | --- | --- | --- |
| `observeCountryHolidays` | boolean | O | Default `true` — apply country holidays unless dismissed. |
| `observeCityHolidays` | boolean | O | Default `true` — apply city holidays unless dismissed. |
| `dismissHolidayIds` | string[] | O | Treat these holiday ids as normal calendar days. |
| `overrides[]` | object | O | Per-holiday behavior override (`holidayId`, `behavior`, optional `paymentWindows` when `behavior` is `"custom"`). |

Polygon `overrides.holidayPolicy` wins over zone.

#### `closures[]` item

| Field | Type | R/O | Meaning |
| --- | --- | --- | --- |
| `id` | string | **R** | Closure id. |
| `closedFrom` | string | **R** | ISO date/datetime start. |
| `closedTo` | string | **R** | ISO date/datetime end (`>= closedFrom`). |
| `locales` | locale map | O | In-app reason (`locales.*.name`). |
| `notes` | string | O | Back-office only. |

#### `paymentWindows[]` item

| Field | Type | R/O | Meaning |
| --- | --- | --- | --- |
| `days` | string[] | **R** | `monday` … `sunday`. |
| `startHour` | string (`HH:mm`) | **R** | Start time, e.g. `"07:00"`. |
| `endHour` | string (`HH:mm`) | **R** | End time, e.g. `"22:00"` or `"24:00"` for midnight end. |

Closed day = no window for that day (legacy `start`/`end` null).

Multiple windows per day set are allowed (e.g. morning + afternoon).

```json
{
  "days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
  "startHour": "07:00",
  "endHour": "22:00"
}
```

#### `seasonalWindows[]` item

| Field | Type | R/O | Meaning |
| --- | --- | --- | --- |
| `id` | string | O | Window id. |
| `label` | string | O | Back-office label (`Zaječar fair`). |
| `effectiveFrom` | string | O | Start of season/event. |
| `effectiveTo` | string | O | End of season/event. |
| `expandsPolygonIds` | string[] | O | Extra polygons active only in this window. |

### `polygons[]`

| Field | Type | R/O | Meaning |
| --- | --- | --- | --- |
| `id` | string | **R** | Polygon id. |
| `zoneId` | string | **R** | Parent zone. |
| `enabled` | boolean | **R** | When `false`, hide this polygon (other polygons of the zone may still show). Production transform sets `true`. |
| `ring` | LatLng[] | **R** | Vertices as `[lat, lon]` pairs; each coord rounded to **6 decimal places**. |
| `ringTruncated` | boolean | O | `true` when `ring` is a shortened sample (examples only). Prefer this over sentinel coordinates. |
| `overrides` | PolygonOverrides | O | Fields that **replace** the parent zone for this polygon only. Empty `{}` = inherit everything. |
| `closures` | Closure[] | O | Temporary **polygon-level** closures (lot/block). |
| `effectiveFrom` / `effectiveTo` | string \| null | O | Effective dating (e.g. staged boundary change). |

#### Override rule

**Any field present under `polygon.overrides` wins over the same field on the parent zone** for locations inside that polygon (hours, products, payment methods, color, eligibility, locales, `fullDayOnly`, …). Belgrade subzones with different hours are the motivating case.

#### `overrides` properties (all optional)

| Field | Type | Meaning |
| --- | --- | --- |
| `color` | string | Override map color. |
| `locales` | locale map | Override name/description/notes. |
| `productIds` | string[] | Ids → `products[]` for this polygon only. |
| `paymentMethodIds` | string[] | Ids → `paymentMethods[]` for this polygon only. |
| `paymentWindows` | PaymentWindow[] | Different hours (`HH:mm`). |
| `eligibility` | Eligibility | Different eligibility. |
| `fullDayOnly` | boolean | Override full-day-only flag. |
| `enabled` | boolean | Override visibility for this polygon. |
| `holidayPolicy` | HolidayPolicy | Override zone holiday policy for this polygon. |

```json
{
  "id": "poly-beograd-zona-1-0",
  "zoneId": "zone-beograd-zona-1",
  "enabled": true,
  "ring": [[44.814512, 20.45659], [44.8141, 20.4572]],
  "overrides": {},
  "effectiveFrom": null,
  "effectiveTo": null
}
```

---

## Commerce layer

### `products[]`

| Field | Type | R/O | Meaning |
| --- | --- | --- | --- |
| `id` | string | **R** | Product id. |
| `legacyId` | integer \| null | O | Old zone id or daily ticket id. |
| `kind` | ProductKind | **R** | `"timed"` \| `"full_day"` \| `"permit"`. See [enums.md](enums.md). |
| `zoneIds` | string[] | O | Ids → `zones[]` this product applies to. |
| `coversZoneIds` | string[] | O | Ids → cheaper `zones[]` also covered by this ticket. |
| `locales` | locale map | O | Product name / description. |
| `color` | string \| null | O | Card / button color. |
| `price` | Money | **R** | List / base price. |
| `pricing` | ProductPricing | **R** | How price scales (hour, minute, ladder, fixed). |
| `validity` | ProductValidity | O | Duration / full-day validity mode. |
| `paymentMethodIds` | string[] | O | Ids → `paymentMethods[]` (**how** this product can be paid). |
| `ruleIds` | string[] | O | Ids → `rules[]` attached to this product. |
| `eligibility` | Eligibility | O | Who may buy. |
| `effectiveFrom` / `effectiveTo` | string \| null | O | Scheduled price/product changes. |

#### `pricing`

| Field | Type | R/O | Meaning |
| --- | --- | --- | --- |
| `mode` | PricingMode | **R** | `"per_hour"` \| `"per_minute"` \| `"fixed"` \| `"ladder"`. See [enums.md](enums.md). |
| `baseDurationMinutes` | integer \| null | O | Default minutes for a single flat unit (legacy `value` / daily `interval`). With a ladder, prefer each step’s `durationMinutes`. |
| `ladder` | LadderStep[] | O | Ordered uneven increments (not hour-index-only). Empty when `mode` is flat `per_hour` / `fixed`. |
| `nightRates` | NightRate[] | O | Night period prices. |
| `seasonalPrices` | SeasonalPrice[] | O | Summer/winter (etc.) price schedules. |
| `byDay` | object | O | Day-keyed pricing overlays (`monday`…`sunday` → partial ladder/price). If omitted, use default pricing for all days. |

```json
"pricing": {
  "mode": "ladder",
  "ladder": [{ "stepIndex": 1, "durationMinutes": 60, "price": { "amount": 80, "currencyId": "rsd" } }],
  "byDay": {
    "saturday": {
      "mode": "ladder",
      "ladder": [{ "stepIndex": 1, "durationMinutes": 60, "price": { "amount": 100, "currencyId": "rsd" } }]
    },
    "sunday": {
      "mode": "ladder",
      "ladder": [{ "stepIndex": 1, "durationMinutes": 60, "price": { "amount": 100, "currencyId": "rsd" } }]
    }
  }
}
```

##### Ladder step (`pricing.ladder[]`)

Supports **uneven** increments (e.g. 1 hour, then 30 minutes). Do **not** assume each step is one hour.

| Field | Type | R/O | Meaning |
| --- | --- | --- | --- |
| `stepIndex` | integer | **R** | 1-based ordinal (1 = first increment, 2 = second, …). Replaces old `hourIndex`. |
| `durationMinutes` | integer | **R** | Length of **this** increment in minutes (`60`, `30`, …). |
| `price` | Money | **R** | Price for this increment. |

Prices live on the **product** ladder (channel-agnostic). SMS `messageSlots[].durationMinutes` should normally **align** with the matching ladder step’s `durationMinutes`, but payment methods do not carry price.

```json
"pricing": {
  "mode": "ladder",
  "baseDurationMinutes": null,
  "ladder": [
    {
      "stepIndex": 1,
      "durationMinutes": 60,
      "price": { "amount": 80, "currencyId": "rsd" }
    },
    {
      "stepIndex": 2,
      "durationMinutes": 30,
      "price": { "amount": 50, "currencyId": "rsd" }
    }
  ],
  "nightRates": [],
  "seasonalPrices": []
}
```

Aligned SMS slots (same durations; price stays on the product):

```json
"messageSlots": [
  { "index": 1, "durationMinutes": 60, "sendWindow": null },
  { "index": 2, "durationMinutes": 30, "sendWindow": null }
]
```

##### Night rate

| Field | Type | R/O | Meaning |
| --- | --- | --- | --- |
| `startHour` | string (`HH:mm`) | **R** | Night window start, e.g. `"22:00"`. |
| `endHour` | string (`HH:mm`) | **R** | Night window end, e.g. `"06:00"` or `"24:00"`. |
| `days` | string[] | O | Limit to certain weekdays. |
| `price` | Money | **R** | Night price. |

##### Seasonal price

| Field | Type | R/O | Meaning |
| --- | --- | --- | --- |
| `label` | string | O | e.g. `summer`. |
| `effectiveFrom` | string | **R** | Season start. |
| `effectiveTo` | string | **R** | Season end. |
| `price` | Money | **R** | Price in that season. |

#### `validity`

| Field | Type | R/O | Meaning |
| --- | --- | --- | --- |
| `mode` | string \| null | O | For full-day: `"calendar_day"` (until end of payment day) or `"rolling_24h"`. `null` for timed products. |
| `durationMinutes` | integer \| null | O | Explicit duration (daily tickets often `1440`). |
| `buttonColor` | string \| null | O | Full-day button color override. |

```json
{
  "id": "prod-timed-beograd-zona-1",
  "kind": "timed",
  "zoneIds": ["zone-beograd-zona-1"],
  "coversZoneIds": [],
  "price": { "amount": 80, "currencyId": "rsd" },
  "pricing": {
    "mode": "per_hour",
    "baseDurationMinutes": 60,
    "ladder": [],
    "nightRates": [],
    "seasonalPrices": []
  },
  "validity": { "mode": null, "durationMinutes": 60, "buttonColor": null },
  "paymentMethodIds": ["pay-sms-beograd-zona-1"],
  "ruleIds": ["rule-max-duration-beograd-zona-1"],
  "eligibility": { "type": "public" }
}
```

```json
{
  "id": "prod-fullday-sabac-celodnevna",
  "kind": "full_day",
  "zoneIds": ["zone-sabac-zona-1", "zone-sabac-zona-2"],
  "price": { "amount": 156, "currencyId": "rsd" },
  "pricing": { "mode": "fixed", "baseDurationMinutes": 1440, "ladder": [], "nightRates": [], "seasonalPrices": [] },
  "validity": { "mode": "calendar_day", "durationMinutes": 1440, "buttonColor": "#FFFFFF" }
}
```

### `paymentMethods[]`

Channel-agnostic. Products/zones reference methods by id. Adding card = new method + app support for that `type` — **do not reshape products or zones**.

| Field | Type | R/O | Meaning |
| --- | --- | --- | --- |
| `id` | string | **R** | Payment method id. |
| `type` | PaymentMethodType | **R** | `"sms"` \| `"webview_card"`. See [enums.md](enums.md). |
| `enabled` | boolean | **R** | Soft switch; disabled methods are not offered. |
| `sms` | object | O | Present when `type` is `sms`. |
| `webviewCard` | object | O | Present when `type` is `webview_card`. |
| `effectiveFrom` / `effectiveTo` | string \| null | O | Effective dating. |

#### `sms`

| Field | Type | R/O | Meaning |
| --- | --- | --- | --- |
| `number` | string | O | Short code / MSISDN to send to. |
| `prefix` | string | O | Message prefix / template start (plate usually appended by app). |
| `messageSlots` | MessageSlot[] | O | Nth SMS duration + optional send windows. |
| `maxDurationMinutes` | integer \| null | O | Cap on cumulative paid minutes (from legacy `restriction_time`). |
| `cooldownAfterMax` | object \| null | O | Block further payments after max until next window. |

##### `messageSlots[]` item

| Field | Type | R/O | Meaning |
| --- | --- | --- | --- |
| `index` | integer | **R** | 1-based SMS ordinal. |
| `durationMinutes` | integer | **R** | Minutes this SMS adds. |
| `sendWindow` | object \| null | O | When this slot may be sent (relative to another slot). |

###### `sendWindow`

| Field | Type | R/O | Meaning |
| --- | --- | --- | --- |
| `relativeToSlotIndex` | integer | O | Usually previous slot. |
| `fromMinutesBeforeEnd` | number | O | Earliest: N minutes before that slot ends. |
| `toMinutesBeforeEnd` | number | O | Latest: M minutes before that slot ends (`0` = at end). |

Belgrade “4th SMS only in last 10 min of 3rd” maps here. Production often yields a **single** slot from legacy `value`.

##### `cooldownAfterMax`

| Field | Type | R/O | Meaning |
| --- | --- | --- | --- |
| `enabled` | boolean | O | Whether cooldown applies. |
| `resumeNextPaymentWindow` | boolean | O | Resume at next `paymentWindows` open. |

```json
{
  "id": "pay-sms-beograd-zona-1",
  "type": "sms",
  "enabled": true,
  "sms": {
    "number": "9111",
    "prefix": "",
    "messageSlots": [
      { "index": 1, "durationMinutes": 60, "sendWindow": null },
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

#### `webviewCard` (future)

| Field | Type | R/O | Meaning |
| --- | --- | --- | --- |
| `urlTemplate` | string | O | Checkout URL with placeholders (`{zoneId}`, `{productId}`, `{plate}`, …). |
| `returnUrlScheme` | string | O | App deep link for payment result. |
| `parameters` | object | O | Extra query/body params for the provider. |

```json
{
  "id": "pay-webview-card-example",
  "type": "webview_card",
  "enabled": false,
  "webviewCard": {
    "urlTemplate": "https://pay.example.com/checkout?zone={zoneId}&product={productId}&plate={plate}",
    "returnUrlScheme": "parkingapp://payment-result",
    "parameters": {}
  }
}
```

### `rules[]`

Typed objects. Apps **skip unknown `type`** values and keep offering known products.

| Field | Type | R/O | Meaning |
| --- | --- | --- | --- |
| `id` | string | **R** | Rule id (referenced from `product.ruleIds`). |
| `type` | RuleType | **R** | Closed enum of known kinds (see [enums.md](enums.md)). Studio rejects unknown; apps ignore unknown at runtime. |
| `notes` | string | O | Back-office explanation. |
| *(type-specific)* | … | O | See below; extra properties allowed for forward compatibility. |

| `type` | Extra fields | Meaning |
| --- | --- | --- |
| `max_duration` | `maxDurationMinutes` | Cap cumulative paid minutes. |
| `cooldown_after_max` | `enabled`, `resumeNextPaymentWindow` | Block further payments after max. |
| `sms_slot_send_window` | `slotIndex`, `relativeToSlotIndex`, `fromMinutesBeforeEnd`, `toMinutesBeforeEnd` | Restrict when slot N may be sent (mirror of SMS sendWindow as a rule). |
| `resident_only` | `eligibility` | Shorthand resident restriction. |
| `seasonal_active` | (use with seasonal windows) | Product/zone only active in windows. |
| `free_initial_minutes` | `minutes` | First N minutes unpaid; then paid product applies. |

```json
{
  "id": "rule-free-initial-prod-x",
  "type": "free_initial_minutes",
  "minutes": 15
}
```

```json
{
  "id": "rule-max-duration-beograd-zona-1",
  "type": "max_duration",
  "maxDurationMinutes": 60,
  "notes": "Mapped from legacy restriction_time"
}
```

### `coveragePolicies[]`

Single policy model for multi-zone locations and “expensive covers cheaper”.

| Field | Type | R/O | Meaning |
| --- | --- | --- | --- |
| `id` | string | **R** | Policy id. |
| `cityId` | string | **R** | City this policy applies to. |
| `onOverlap` | CoverageOnOverlap | **R** | `"offer_highest_rank"` \| `"offer_all"` \| `"offer_none"`. See [enums.md](enums.md). |
| `zones` | array | **R** | Per-zone rank + coverage list. |

#### `zones[]` item

| Field | Type | R/O | Meaning |
| --- | --- | --- | --- |
| `zoneId` | string | **R** | Zone id. |
| `rank` | integer | **R** | Higher = more “expensive” / preferred on overlap. |
| `coversZoneIds` | string[] | O | Zones covered when this zone’s ticket is bought. |

```json
{
  "id": "coverage-beograd",
  "cityId": "city-beograd",
  "onOverlap": "offer_highest_rank",
  "zones": [
    {
      "zoneId": "zone-beograd-zona-a",
      "rank": 120600,
      "coversZoneIds": []
    }
  ]
}
```

Generated data ranks zones by price; `coversZoneIds` is empty until back office fills the real graph.

### `residentPermits[]`

| Field | Type | R/O | Meaning |
| --- | --- | --- | --- |
| `id` | string | **R** | Permit id. |
| `locales` | locale map | O | Permit name / description. |
| `validZoneIds` | string[] | **R** | Zones where this permit is valid. |
| `eligibility` | Eligibility | O | Who holds / may use it. |
| `effectiveFrom` / `effectiveTo` | string \| null | O | Permit validity window. |

### `fines[]`

| Field | Type | R/O | Meaning |
| --- | --- | --- | --- |
| `id` | string | **R** | Fine id. |
| `operatorId` | string \| null | O | Issuing operator. |
| `zoneIds` | string[] | O | Zones where this fine applies. |
| `amount` | Money | **R** | Fine amount. |
| `discount` | object \| null | O | Early-payment discount. |
| `locales` | locale map | O | Fine labels. |

#### `discount`

| Field | Type | R/O | Meaning |
| --- | --- | --- | --- |
| `amount` | Money | O | Fixed discount amount. |
| `percent` | number | O | Percent discount (e.g. `50`). |
| `periodDurationMinutes` | integer | O | How long the discount is available after issue. |

```json
{
  "id": "fine-example",
  "operatorId": null,
  "zoneIds": ["zone-beograd-zona-1"],
  "amount": { "amount": 5000, "currencyId": "rsd" },
  "discount": {
    "percent": 50,
    "periodDurationMinutes": 1440
  }
}
```

---

## Versioning behavior (apps)

| Mechanism | Behavior |
| --- | --- |
| `dataVersion` | Monolith revision for cache / “is this newer?” when using a single file. |
| `minAppVersion` | If app &lt; this, refuse config (prompt update). |
| Unknown `rules[].type` | Ignore that rule; keep product if still usable. |
| Unknown `paymentMethods[].type` | Hide that payment path. |
| Unknown `eligibility.type` | Treat as not matching / hide offer (safer than granting access). |

### Production delivery (manifest + shared + cities)

Apps in production should fetch **`manifest.json`**, then **`shared.json`** and
per-city files — not the full monolith on every launch. See
**[delivery-manifest.md](delivery-manifest.md)** for the full contract.

| Flag | Behavior |
| --- | --- |
| `cities[].forceUpdate: true` | Hard refresh that city **before** using it (e.g. SMS/price/rules changed). Do not keep serving stale cache for parking in that city. |
| `cities[].forceUpdate: false` | Soft update; refresh in background. |
| `shared.forceUpdate` | Hard vs soft refresh of locales / currencies / countries / operators. |
| Manifest root `forceUpdate` | Global/schema refresh and/or app gate via `minAppVersion`. |

Bump each city `version` on any city content change. Set `forceUpdate: true`
when payment/SMS/price/rules would make old data wrong or illegal; leave
`false` for pure map/cosmetic tweaks if desired.

Split a monolith with `scripts/split_parking_config.py`. Tiny sample:
[`examples/delivery/`](../examples/delivery/).

---

## Production → field mapping (cheat sheet)

| Legacy | New field |
| --- | --- |
| `version` | `source.legacyVersion` (new `dataVersion` starts fresh) |
| `currency[]` | `currencies[]` |
| `cities` / `montenegro_cities` | `countries` + `cities[]` |
| city name / cases | `city.locales` |
| `Zones[]` | `zones[]` + `polygons[]` + timed `products[]` + SMS `paymentMethods[]` |
| `parking_hours` (numeric hours) | `zone.paymentWindows` with `HH:mm` strings (`7` → `"07:00"`, `24` → `"24:00"`) |
| zone / polygon visibility | `enabled: true` (all from prod) |
| coordinates | rounded to 6 decimal places |

| `value` | `pricing.baseDurationMinutes` + `sms.messageSlots[0].durationMinutes` |
| `restriction` / `restriction_time` | `rules` `max_duration` + `sms.maxDurationMinutes` + cooldown |
| `daily_tickets[]` | `products` with `kind: "full_day"` |
| `sms_number` / `sms_prefix` / `sms_prefix_daily` | `paymentMethods[].sms` |
| `forZones` | `product.zoneIds` |
| `working_days_override` | `zone.workingDayOverrides` |
| `info_note` | `locales.*.infoNote` |

---

## Related files

| Path | Role |
| --- | --- |
| [schema.md](schema.md) | Concept guide |
| [client-resolve.md](client-resolve.md) | App resolve algorithm |
| [evaluation-order.md](evaluation-order.md) | Full precedence cheat sheet |
| [parking-config.schema.json](parking-config.schema.json) | JSON Schema |
| [delivery-manifest.md](delivery-manifest.md) | Manifest + shared + per-city delivery + `forceUpdate` |
| [geojson-import.md](geojson-import.md) | Local GeoJSON → monolith (confidential) |
| [../data/parking-config.generated.json](../data/parking-config.generated.json) | Full generated config (monolith) |
| [../examples/belgrade-snippet.json](../examples/belgrade-snippet.json) | Belgrade excerpt |
| [../examples/delivery/](../examples/delivery/) | Minimal manifest delivery stub |
| [../examples/client-resolve/](../examples/client-resolve/) | Golden resolve fixtures |
| [requirements.md](requirements.md) | Product requirements |
| [project-context.md](project-context.md) | Locked decisions |
