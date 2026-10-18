# Closed string enums (mobile cheat sheet)

Stable closed sets for Swift/Kotlin enums. Schema: `$defs` in [parking-config.schema.json](parking-config.schema.json). Studio Validate **errors** on values outside these sets. Apps may still ignore *unknown* rule/payment types at runtime for older builds, but **publish quality** requires only known values.

Mental model: one `String`/`rawValue` enum per table below.

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

`sr-Latn` · `sr-Cyrl` · `en` · `ru`

All four required on every `LocalesMap` (see [field-reference.md](field-reference.md) locales contract).

### `shared.client` (and monolith `client`)

| Field | Typical value |
| --- | --- |
| `supportedLocales` | `["sr-Latn","sr-Cyrl","en","ru"]` |
| `localeFallback` | `["sr-Latn","en","sr-Cyrl","ru"]` |

Apps resolve display strings with UI locale, then `localeFallback` ([client-resolve.md](client-resolve.md)). Studio split/export always emits this block.

## `WeekdayKey`

`monday` · `tuesday` · `wednesday` · `thursday` · `friday` · `saturday` · `sunday`

## `ProductKind`

`timed` · `full_day` · `permit`

## `PaymentMethodType`

`sms` · `webview_card`

## `PricingMode`

`per_hour` · `per_minute` · `fixed` · `ladder`

## `ValidityMode`

`calendar_day` · `rolling_24h`

(May be `null` / omitted on the product.)

## `EligibilityType`

`public` · `residents`

Closed for v1 (no vehicle-class hooks yet).

## `RuleType`

`max_duration` · `cooldown_after_max` · `sms_slot_send_window` · `resident_only` · `seasonal_active` · `free_initial_minutes`

| Type | Typical fields |
| --- | --- |
| `max_duration` | `maxDurationMinutes` |
| `cooldown_after_max` | `enabled`, `resumeNextPaymentWindow` |
| `sms_slot_send_window` | `slotIndex`, `relativeToSlotIndex`, `fromMinutesBeforeEnd`, `toMinutesBeforeEnd` |
| `resident_only` | `eligibility` |
| `seasonal_active` | (with seasonal windows) |
| `free_initial_minutes` | `minutes` |

New rule kinds require a schema bump + newest app support; older apps ignore unknown `type` at runtime. Studio rejects unknown types on Validate.

## `HolidayBehavior`

`free` · `closed` · `weekday` · `sunday`

## `HolidayOverrideBehavior`

`free` · `closed` · `weekday` · `sunday` · `custom`

(`custom` requires `paymentWindows`.)

## `CoverageOnOverlap`

`offer_highest_rank` · `offer_all` · `offer_none`

---

## Booleans (not string enums)

`enabled`, `forceUpdate`, `fullDayOnly`, `ringTruncated`, `observeCountryHolidays`, `observeCityHolidays`, SMS `cooldownAfterMax.enabled`, etc. — plain booleans.
