# Parking config — project context

## Goal

Replace the current flat parking JSON with a **rule-data** format so new rules and features can ship via remote config without forcing app updates (after the one-time jump to this format).

## Decisions (2026-10-18)

| Topic | Decision |
| --- | --- |
| Timezone | Required — per country and/or city |
| Inheritance | Polygon overrides zone for any differing rule, value, price, hours, etc. |
| Payment channels | SMS now; format must easily add **card via webview** (priority). Channel-agnostic products + per-channel payment config |
| Eligibility | Residents for now; structure for user/vehicle eligibility generally |
| Legacy app | No compatibility with current format — force update for cutover is fine |
| Future rules | New rule kinds OK if only newest app supports them; older apps keep working for rules they know |
| Money | `{ "amount": number, "currencyId": string }` everywhere |
| IDs | Fresh stable string IDs; optional `legacyId` for review |
| Back office | All fields readable/self-explanatory for non-developers |
| Locales | Maps per locale id; grammatical cases nested under locale |
| Coverage | Single policy model for multi-zone overlap + expensive-covers-cheaper |
| Effective dating | `effectiveFrom` / `effectiveTo` where values can change on a schedule |

## Architecture

Three layers:

1. **Catalog** — countries, cities, operators, currencies, locales  
2. **Geography** — zones → polygons (polygon overrides zone)  
3. **Products + rules + payment methods** — what is sold; rules by reference; payment pluggable (`sms`, `webview_card`, …)

## Status

- Decisions locked (including money shape).
- **GitHub repo:** [https://github.com/nebojsanikolic/new-json-format](https://github.com/nebojsanikolic/new-json-format)  
  Schema + full production transform live there (`data/parking-config.generated.json`, `docs/schema.md`, JSON Schema).
- Local / Context copies also under the Project store `docs/` while push/auth was being set up.
- Next (product/app): wire cutover, back-office editor, fill coverage `coversZoneIds` and multi-slot SMS windows that were previously hard-coded.

## Related

- Requirements: [requirements.md](requirements.md)
- Legacy shape: [legacy-schema.json](legacy-schema.json)
