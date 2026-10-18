# Closed string enums (mobile cheat sheet)

Canonical meanings for mobile enums; [field-reference.md](field-reference.md) has full field docs.

Stable closed sets for Swift/Kotlin enums. Schema: `$defs` in [parking-config.schema.json](parking-config.schema.json). Studio Validate **errors** on values outside these sets. Apps may still ignore *unknown* rule/payment types at runtime for older builds, but **publish quality** requires only known values.

Mental model: one `String`/`rawValue` enum per table below. Runtime stacking: [evaluation-order.md](evaluation-order.md) · resolve algorithm: [client-resolve.md](client-resolve.md).

| Schema `$defs` | Field(s) |
| --- | --- |
| `localeId` | `locales` catalog `id`, `LocalesMap` keys, `languageSortOrder[]`, `updateDescription` keys |
| `weekdayKey` | `paymentWindows[].days[]`, `nightRates[].days[]`, `pricing.byDay` keys |
| `productKind` | `products[].kind` |
| `paymentMethodType` | `paymentMethods[].type` |
| `pricingMode` | `pricing.mode`, `pricing.byDay.*.mode` |
| `validityMode` | `product.validity.mode` (nullable) |
| `eligibilityType` | `eligibility.type` |
| `ruleType` | `rules[].type` |
| `holidayBehavior` | `holidays[].defaultBehavior` |
| `holidayOverrideBehavior` | `holidayPolicy.overrides[].behavior` |
| `coverageOnOverlap` | `coveragePolicies[].onOverlap` |

---

## `LocaleId`

All four required on every `LocalesMap` (see [field-reference.md](field-reference.md) locales contract).

| Value | Meaning |
| --- | --- |
| `sr-Latn` | Serbian in Latin script (primary UI locale for Serbia). |
| `sr-Cyrl` | Serbian in Cyrillic script. |
| `en` | English. |
| `ru` | Russian. |

### `shared.client` (and monolith `client`)

| Field | Typical value | Meaning |
| --- | --- | --- |
| `supportedLocales` | `["sr-Latn","sr-Cyrl","en","ru"]` | Locales the app UI must support for this config. |
| `localeFallback` | `["sr-Latn","en","sr-Cyrl","ru"]` | Ordered fallback when a `LocalesMap` string is empty for the UI locale. |

Apps resolve display strings with UI locale, then `localeFallback` ([client-resolve.md](client-resolve.md)). Studio split/export always emits this block.

---

## `WeekdayKey`

Used in payment windows, night rates, and `pricing.byDay` keys.

| Value | Meaning |
| --- | --- |
| `monday` | Monday |
| `tuesday` | Tuesday |
| `wednesday` | Wednesday |
| `thursday` | Thursday |
| `friday` | Friday |
| `saturday` | Saturday |
| `sunday` | Sunday |

---

## `ProductKind`

What the product sells (`products[].kind`).

| Value | Meaning | When to use |
| --- | --- | --- |
| `timed` | Pay-as-you-go duration (hour / ladder / SMS slots). | Street zones with incremental parking. |
| `full_day` | One ticket covering a full day (or rolling 24h — see ValidityMode). | Daily tickets / lots that sell only all-day. |
| `permit` | Longer-term / resident-style entitlement (not a casual timed buy). | Resident or multi-day permits. |

---

## `PaymentMethodType`

How the user pays (`paymentMethods[].type`). Unknown types: **hide** that channel ([evaluation-order.md](evaluation-order.md)).

| Value | Meaning | When to use |
| --- | --- | --- |
| `sms` | Pay by SMS short-code (`sms.number`, `prefix`, `messageSlots`). | Current Serbia/Montenegro default. |
| `webview_card` | Pay by card inside an in-app webview (`webviewCard` config). | When card checkout is enabled structurally. |

---

## `PricingMode`

How the product’s price is computed (`pricing.mode`). Overlay order: byDay → nightRates → seasonalPrices → default ([evaluation-order.md](evaluation-order.md)).

| Value | Meaning | When to use |
| --- | --- | --- |
| `per_hour` | Flat price for each hour (or `baseDurationMinutes` unit). | Simple hourly zones without uneven steps. |
| `per_minute` | Price scales by minute. | Rare; minute-metered tariffs. |
| `fixed` | Single fixed amount for the product (typical full-day ticket). | Daily tickets / flat fee. |
| `ladder` | Ordered uneven increments via `pricing.ladder[]` (`stepIndex`, `durationMinutes`, `price`). | 60 then 30 min (or similar) steps. |

---

## `ValidityMode`

How long a full-day / permit purchase lasts (`product.validity.mode`). Timed products usually use `null`.

| Value | Meaning | When to use |
| --- | --- | --- |
| `calendar_day` | Valid until end of the payment calendar day (local timezone). | Classic “daily ticket until midnight”. |
| `rolling_24h` | Valid for 24 hours from purchase/start. | Lots that sell a rolling day, not midnight cutoff. |

---

## `EligibilityType`

Who may use the zone / product (`eligibility.type`). Closed for v1 (no vehicle-class hooks yet). Unknown: treat as **no match** / hide offer.

| Value | Meaning | When to use |
| --- | --- | --- |
| `public` | Anyone may buy / park under normal rules. | Default on-street and open lots. |
| `residents` | Restricted to residents (permit / eligibility checks). | Resident zones or resident-only products. |

---

## `RuleType`

Rules attached via `product.ruleIds`. Unknown `type` at runtime: **ignore** that rule; Studio Validate **errors**. New kinds need a schema bump + newest app.

| Value | Meaning | When to use |
| --- | --- | --- |
| `max_duration` | Cap how many paid minutes can accumulate in one stay (`maxDurationMinutes`). | Legacy `restriction_time` / max stay. |
| `cooldown_after_max` | After hitting max, block further payments until the next payment window (`enabled`, `resumeNextPaymentWindow`). | “Maxed out until tomorrow / next window”. |
| `sms_slot_send_window` | Gate when SMS slot N may be sent (relative minutes before another slot ends). | Belgrade-style “4th SMS only in last 10 minutes” patterns. |
| `resident_only` | Shorthand that the offer is residents-only (pairs with eligibility). | Resident products without a fuller permit model. |
| `seasonal_active` | Product/zone only active inside seasonal windows. | Event / seasonal lots. |
| `free_initial_minutes` | First `minutes` are unpaid; paid product applies after that. | Short free arrival before charging starts (not a grace after hours). |

Field shapes: [field-reference.md](field-reference.md) · stacking: [evaluation-order.md](evaluation-order.md).

---

## `HolidayBehavior`

Catalog default for a holiday date (`holidays[].defaultBehavior`). Applied after polygon/zone holiday policy ([evaluation-order.md](evaluation-order.md)).

| Value | Meaning | When to use |
| --- | --- | --- |
| `free` | No collection that day (parking free / not charged). | Public holidays that are free parking. |
| `closed` | Not in service (do not sell). | Holidays when parking is closed. |
| `weekday` | Use **weekday** (Mon–Fri style) payment windows for that date. | Holidays that follow a normal workday schedule. |
| `sunday` | Use **sunday** payment windows for that date. | Holidays that follow Sunday hours. |

---

## `HolidayOverrideBehavior`

Per-zone / polygon override (`holidayPolicy.overrides[].behavior`). Same four as above, plus:

| Value | Meaning | When to use |
| --- | --- | --- |
| `free` | Override: no collection that holiday. | Zone freer than catalog default. |
| `closed` | Override: closed that holiday. | Zone stricter than catalog. |
| `weekday` | Override: use weekday windows. | Zone keeps workday hours on that holiday. |
| `sunday` | Override: use Sunday windows. | Zone uses Sunday hours on that holiday. |
| `custom` | Use the override’s own `paymentWindows` (required). | One-off holiday hours for that zone/polygon. |

---

## `CoverageOnOverlap`

What to offer when GPS / map hits multiple zones (`coveragePolicies[].onOverlap`). Rank is higher = preferred / “more expensive”; distinct from `zone.displayOrder`.

| Value | Meaning | When to use |
| --- | --- | --- |
| `offer_highest_rank` | Offer only the highest-ranked overlapping zone. | Typical city: one clear winner on overlap. |
| `offer_all` | Offer every overlapping zone (user picks). | Cities that intentionally show multiple options. |
| `offer_none` | Offer nothing when overlap is ambiguous. | Strict “must be unambiguous pin” cities. |

---

## Booleans (not string enums)

`enabled`, `forceUpdate`, `fullDayOnly`, `ringTruncated`, `observeCountryHolidays`, `observeCityHolidays`, SMS `cooldownAfterMax.enabled`, etc. — plain booleans, not closed string enums.
