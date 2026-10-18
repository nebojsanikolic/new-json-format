# Evaluation order (app cheat sheet)

One page for mobile/back-office: how stacked rules interact. Storage stays normalized; clients resolve at runtime ([client-resolve.md](client-resolve.md)).

**Domain:** public on-street / open lots run by local parking services — not private garages. Outside `paymentWindows` = not collected; vehicle may stay until the next window.

---

## Master order (first match wins / stop)

When deciding “can the user park / buy here **now**?”:

1. **Missing entity** — unknown `zoneId` / wrong city file → unavailable.
2. **`enabled`** — polygon `enabled` if resolving a polygon; else zone `enabled`. `false` → hide.
3. **Temporary closures** — active `closures[]` on **polygon** first, then **zone** (`closedFrom`…`closedTo`, optional localized reason). Active → closed / not in service.
4. **`effectiveFrom` / `effectiveTo`** — polygon, then zone (later also product & payment method). Outside → inactive.
5. **Seasonal active window** — if the zone is seasonal-only (`seasonalWindows`), require `now` inside an active window (and honor `expandsPolygonIds` when relevant).
6. **Holidays** — see below → may clear hours (`free`), close, or swap windows.
7. **`paymentWindows`** (after holiday adjustment) — if `now` outside all windows → **not collected** (no short grace field).
8. **Eligibility** — `public` / `residents` (effective polygon → zone → product).
9. **Products + payment methods + rules** — what/how to sell (filter by dating, enabled, known types).
10. **Pricing overlays** — `byDay` → `nightRates` → `seasonalPrices` → default ladder/`price`.

---

## Polygon vs zone

Any field **present and non-null** under `polygon.overrides` replaces the same field on the zone for that polygon only:

`color`, `locales`, `productIds`, `paymentMethodIds`, `paymentWindows`, `eligibility`, `fullDayOnly`, `enabled`, `holidayPolicy`.

`null` on an override field = inherit zone. Omitting the whole `overrides` object (or `overrides: null`) = inherit all.

---

## Holidays

**Catalog:** `shared.holidays` (country, no `cityId`) + city-slice `holidays` (`cityId` set).

**Policy** (polygon `holidayPolicy` → else zone):

| Flag / list | Effect |
| --- | --- |
| `observeCountryHolidays` (default true) | Apply matching country holidays |
| `observeCityHolidays` (default true) | Apply matching city holidays |
| `dismissHolidayIds` | Treat as normal calendar day |
| `overrides[]` | Per-`holidayId` behavior (`free` / `closed` / `weekday` / `sunday` / `custom` + windows) |

**Behavior** when a holiday applies and is not dismissed:

| Value | Meaning |
| --- | --- |
| `free` | No collection that day |
| `closed` | Not in service |
| `weekday` / `sunday` | Use windows for those day names |
| `custom` | Use override `paymentWindows` |

---

## Payment windows

- Closed day = no window for that weekday (after holiday logic).
- Multiple windows per day allowed.
- **Outside windows = not collected**; stay until next open window is OK for this domain.

---

## Pricing (timed product)

For the chargeable instant:

1. `pricing.byDay[weekday]` if set  
2. else matching `nightRates[]`  
3. else matching `seasonalPrices[]`  
4. else default `pricing.mode` / `ladder` / top-level `price`

---

## Products & payments

| Topic | Rule |
| --- | --- |
| Product list | Effective `productIds` ∪ products referencing zone via `zoneIds` / `coversZoneIds` |
| `fullDayOnly` | Offer only `full_day` products when effective flag true |
| Payment channels | Product `paymentMethodIds` if non-empty, else zone; skip `enabled: false` |
| Unknown `paymentMethods[].type` | Hide that channel; keep known ones |
| SMS details | `sms.number`, `prefix`, `messageSlots`, `maxDurationMinutes`, `cooldownAfterMax` |
| Slot gating | `messageSlots[].sendWindow` and/or rule `sms_slot_send_window` |

---

## Rules (`rules[]` via `product.ruleIds`)

| `type` | Effect |
| --- | --- |
| `max_duration` | Cap cumulative paid minutes |
| `cooldown_after_max` | Block further pay after max |
| `free_initial_minutes` | First `minutes` unpaid |
| `sms_slot_send_window` | When slot N may be sent |
| `resident_only` | Eligibility shorthand |
| `seasonal_active` | Tie to seasonal windows |

**Unknown `rule.type`:** ignore for publish? Studio Validate **errors**. At runtime, older apps **ignore** unknown types and keep selling what they understand. New kinds need schema bump + newest app for that feature.

---

## Coverage & list UI

| Concern | Field |
| --- | --- |
| GPS hits 2+ zones | `coveragePolicies[].onOverlap` + `zones[].rank` |
| Expensive covers cheaper | `coversZoneIds` on policy entries / product |
| City zone list order | `zone.displayOrder` (not coverage rank) |

---

## Locales

- Every in-app `locales` object: all four keys `sr-Latn`, `sr-Cyrl`, `en`, `ru` ([enums.md](enums.md)).
- Pick string: UI locale, then `shared.client.localeFallback`.
- `supportedLocales` lists the closed set.

---

## Effective dating reminder

Optional `effectiveFrom` / `effectiveTo` on zone, polygon, product, payment method (and similar). `null` = always (within other rules). Prefer explicit `null` in JSON for stable optional fields ([field-reference.md](field-reference.md) conventions).

---

## Quick “blocked” checklist

```
!enabled → hide
active closure → closed (+ reason)
outside effective* → inactive
seasonal-only miss → inactive
holiday closed → closed
holiday free / outside paymentWindows → not collected
eligibility fail → hide purchase
no known products/payments left → nothing to sell
```
