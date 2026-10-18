# Client resolve guide (mobile)

How an app turns a **normalized** city bundle + `shared.json` into what to show/sell at a pin — without denormalized lookup tables in the JSON.

Inputs:

| Input | Source |
| --- | --- |
| Shared catalog | `shared.json` (`locales`, `currencies`, `countries`, `operators`, country `holidays`, `client`) |
| City slice | `cities/{cityId}.json` |
| Location | `zoneId` and optional `polygonId` (from map hit / GPS) |
| UI locale | selected `LocaleId` |
| Now | instant in the **city/country timezone** |

Storage stays normalized (arrays + id refs). Build your own dictionaries in memory (`zonesById`, …) — they are **not** shipped in the files.

Companion: [evaluation-order.md](evaluation-order.md) · [enums.md](enums.md) · fixtures in [`examples/client-resolve/`](../examples/client-resolve/).

---

## 0. Load & index

1. Fetch manifest → refresh `shared.json` / city file per `forceUpdate` / versions / checksums.
2. Build maps: `zoneById`, `polygonById`, `productById`, `paymentById`, `ruleById`, `holidayById`, `currencyById`, `operatorById`.
3. Read `shared.client.supportedLocales` and `shared.client.localeFallback` (defaults if missing: four locales; fallback `["sr-Latn","en","sr-Cyrl","ru"]`).

---

## 1. Resolve entity pair

```
zone = zoneById[zoneId]
polygon = polygonId ? polygonById[polygonId] : null
assert polygon == null || polygon.zoneId == zone.id
```

If `zone` missing → not in this city file; stop.

---

## 2. Visibility / hard blocks (stop if blocked)

Apply in order (see [evaluation-order.md](evaluation-order.md)):

1. **Enabled** — `polygon.enabled` if polygon present, else `zone.enabled`. If false → hide.
2. **Closures** — active if `now ∈ [closedFrom, closedTo]`  
   - Use `polygon.closures` if non-empty, else `zone.closures` (polygon list replaces zone list when present and non-empty; empty `[]` means none at that level — fall back to zone).  
   - Prefer: check polygon closures first; if any active → closed. Else zone closures.
3. **effectiveFrom / effectiveTo** — on polygon then zone (and later product/payment). Outside window → not active.
4. **Seasonal-only** — if zone has `seasonalWindows` that define the only active periods, require `now` inside one (when used as seasonal-only lots).

If blocked → show closed / not available (optional localized closure `locales` reason).

---

## 3. Effective display fields (polygon overrides zone)

For each field, **if the key is present under `polygon.overrides` and not `null`, use it; else zone**:

| Field | Notes |
| --- | --- |
| `color` | Map fill / card |
| `locales` | Full `LocalesMap` (four keys) |
| `productIds` | What can be bought |
| `paymentMethodIds` | How to pay (zone-level default) |
| `paymentWindows` | Collection hours |
| `eligibility` | `public` / `residents` |
| `fullDayOnly` | boolean |
| `enabled` | already applied |
| `holidayPolicy` | observe / dismiss / overrides |

Scalars that are `null` mean “unset / inherit” for overrides; on the **zone** itself, `null` means “no value” (e.g. `operatorId: null`).

**Display strings** — pick locale with fallback:

```
chain = [uiLocale] + client.localeFallback  (dedupe)
for id in chain:
  if locales[id].name: use it
```

Same for `description` / `infoNote`.

---

## 4. Hours (`paymentWindows`)

1. Start from effective `paymentWindows` (polygon → zone).
2. Apply **holiday policy** for today’s calendar date (city timezone):
   - Collect applicable holidays: country (`shared.holidays` matching `countryId`, no `cityId`) + city (`city.holidays` / slice `holidays` with `cityId`).
   - Filter by `holidayPolicy.observeCountryHolidays` / `observeCityHolidays` (default true).
   - Remove `dismissHolidayIds`.
   - If an `overrides[]` entry matches `holidayId`, use its `behavior` (`custom` → that entry’s `paymentWindows`).
   - Else use holiday `defaultBehavior`: `free` (no collection), `closed` (not in service), `weekday` / `sunday` (filter windows to those days).
3. Outside any window → **not collected**; car may stay until the next window opens (no grace field).

---

## 5. Products to offer

1. Resolve product id list: effective `productIds`, plus any `products[]` whose `zoneIds` / `coversZoneIds` include this zone (union; de-dupe).
2. Filter each product by `enabled` semantics, `effectiveFrom`/`effectiveTo`, `eligibility`, and kind rules (`fullDayOnly` zone → only `full_day` products, etc.).
3. Attach `paymentMethodIds` from product if non-empty, else zone effective list.
4. Resolve each payment method; skip `enabled: false`; skip unknown `type` (hide that channel).
5. Resolve `ruleIds` → rules; **ignore unknown `rule.type`** for selling, but still hide features that depend on unknown rules if unsafe.

---

## 6. Price for “now”

For a timed product:

1. If `pricing.byDay[weekday]` present → use that overlay’s ladder/mode/price.
2. Else if a `nightRates[]` entry matches weekday + clock → that price.
3. Else if a `seasonalPrices[]` entry matches `now` → that price.
4. Else default `pricing.ladder` / `price` / `mode`.

---

## 7. SMS / max stay / free initial

From the chosen payment method + rules:

| Concern | Where |
| --- | --- |
| SMS number / prefix / slots | `paymentMethod.sms` |
| Slot send window | `messageSlots[].sendWindow` (and/or `sms_slot_send_window` rule) |
| Max paid minutes | `rule` `max_duration` and/or `sms.maxDurationMinutes` |
| Cooldown after max | `cooldown_after_max` rule / `sms.cooldownAfterMax` |
| Free first N minutes | `rule` `free_initial_minutes.minutes` |

---

## 8. Coverage / list order

- **Map overlap** — `coveragePolicies` for the city: `onOverlap` + per-zone `rank` + `coversZoneIds`.
- **UI list order** — `zone.displayOrder` (1…n in city), not the same as coverage rank.

---

## 9. Resolved offer shape (suggested)

Apps may use any structure; fixtures use:

```json
{
  "zoneId": "…",
  "polygonId": "…",
  "locale": "en",
  "at": "2026-10-18T12:00:00+02:00",
  "available": true,
  "blockedReason": null,
  "displayName": "…",
  "description": "…",
  "color": "#E53935",
  "paymentWindows": [ … ],
  "products": [
    {
      "id": "…",
      "kind": "timed",
      "displayName": "…",
      "price": { "amount": 80, "currencyId": "rsd" },
      "paymentMethods": [ { "id": "…", "type": "sms", "sms": { … } } ],
      "rules": { "maxDurationMinutes": 180, "freeInitialMinutes": null }
    }
  ]
}
```

See golden files under [`examples/client-resolve/`](../examples/client-resolve/).
