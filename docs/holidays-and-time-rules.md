# Holidays & time rules (accepted)

Status: **accepted** (schema + Studio Catalog/inspector). Items #8–#12 are **not** in schema. There is **no grace-minutes field** — see [Outside payment windows](#outside-payment-windows-public-on-street).

Full stacked precedence (enabled, closures, dating, holidays, windows, pricing, locales, …): **[evaluation-order.md](evaluation-order.md)**. Resolve algorithm: **[client-resolve.md](client-resolve.md)**.

Shared `LocalesMap` contract: **all four** keys required on every in-app locales object — `sr-Latn`, `sr-Cyrl`, `en`, `ru` (no partial maps).

## Country + city holidays

Top-level `holidays[]`. Scope with `countryId` and/or `cityId` (municipal when `cityId` set).

```json
"holidays": [
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
  },
  {
    "id": "hol-beograd-2027-04-16",
    "countryId": "rs",
    "cityId": "city-beograd",
    "date": "2027-04-16",
    "locales": {
      "sr-Latn": { "name": "Dan Beograda" },
      "sr-Cyrl": { "name": "Дан Београда" },
      "en": { "name": "Belgrade Day" },
      "ru": { "name": "День Белграда" }
    },
    "defaultBehavior": "free"
  }
]
```

`defaultBehavior`: `free` | `closed` | `weekday` | `sunday`.

Delivery: no `cityId` → `shared.json`; with `cityId` → that city’s slice.

## Dismiss / override (zone + polygon)

```json
"holidayPolicy": {
  "observeCountryHolidays": true,
  "observeCityHolidays": true,
  "dismissHolidayIds": ["hol-rs-2027-01-01"],
  "overrides": [
    {
      "holidayId": "hol-rs-2027-01-01",
      "behavior": "custom",
      "paymentWindows": [
        { "days": ["thursday"], "startHour": "10:00", "endHour": "14:00" }
      ]
    }
  ]
}
```

Polygon `overrides.holidayPolicy` wins over zone.

## Day-based prices

Optional `product.pricing.byDay` (weekday keys). If omitted, use default ladder/price.

```json
"byDay": {
  "saturday": {
    "mode": "ladder",
    "ladder": [
      { "stepIndex": 1, "durationMinutes": 60, "price": { "amount": 100, "currencyId": "rsd" } }
    ]
  }
}
```

## Free first N minutes

Typed rule (apps ignore unknown types):

```json
{ "id": "rule-free-initial-x", "type": "free_initial_minutes", "minutes": 15 }
```

Attach via `product.ruleIds`.

## Temporary closures (zone + polygon)

```json
"closures": [
  {
    "id": "closure-zone-x-1",
    "closedFrom": "2027-03-01",
    "closedTo": "2027-03-15",
    "locales": {
      "sr-Latn": { "name": "Radovi" },
      "en": { "name": "Construction" }
    }
  }
]
```

Polygon-level `closures[]` is required for lot/block closures.

## Precedence (apps) — short note

1. Polygon/zone temporary closure / `enabled: false`
2. `effectiveFrom` / `effectiveTo`
3. Seasonal active window (if seasonal-only)
4. Holiday policy (polygon → zone → catalog default)
5. Weekly `paymentWindows` (+ price night/seasonal/`byDay` overlays)
6. Product + payment method + rules (incl. `free_initial_minutes`)

## Locale audit (user-facing → locale map)

| Entity / field | Status |
| --- | --- |
| Zone / city / country / product / operator / fine `locales` | Already locale maps |
| Holiday `locales.name` | Required locale map |
| Closure reason | `locales.name` |
| Manifest `updateDescription` | When a locale→string map, **all four** keys required |
| Zone `infoNote` | Under `locales.*.infoNote` |
| `seasonalWindows[].label`, `rules[].notes`, `eligibility.notes`, `source.notes` | Back-office plain strings OK |

## Outside payment windows (public on-street)

This config is for **public** spaces run by local parking services (not closed garages / private lots).

If collection runs until **21:00**, the car may stay until the **next** `paymentWindows` open (e.g. next morning). Time outside windows is simply not collected — no separate “grace minutes” field.

## Explicitly not in schema

- Short grace after window end (#5) — **not needed** for this domain (overnight until next window is free by `paymentWindows`)
- Pay window ≠ enforcement window (#8)
- Payment method by date (#9)
- Vehicle constraints beyond residents (#10)
- Capacity (#11)
- Formal precedence as a product feature (#12) — this short note only
- Movable-holiday formulas / half-days — not requested now

## Studio

- Catalog → **Holidays** tab (country + city)
- Zone/polygon inspector → holiday observe/dismiss, closures, weekend `byDay`, free-initial toggle
- Validate → unique holiday ids; dismiss/override refs exist; closure date order; holiday names non-empty
