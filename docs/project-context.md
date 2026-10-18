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
- **GitHub repo (live):** [https://github.com/nebojsanikolic/new-json-format](https://github.com/nebojsanikolic/new-json-format)  
  - Generated data: [`data/parking-config.generated.json`](https://github.com/nebojsanikolic/new-json-format/blob/main/data/parking-config.generated.json)  
  - Field reference: [`docs/field-reference.md`](https://github.com/nebojsanikolic/new-json-format/blob/main/docs/field-reference.md)  
  - Concept guide: [`docs/schema.md`](https://github.com/nebojsanikolic/new-json-format/blob/main/docs/schema.md)  
  - JSON Schema: [`docs/parking-config.schema.json`](https://github.com/nebojsanikolic/new-json-format/blob/main/docs/parking-config.schema.json)
- Project store `docs/` mirrors the same materials for Context.
- Format tweaks (2026-10-18): payment/night hours as `"HH:mm"`; zone/polygon `enabled`; lat/lng rounded to 6 dp; id refs documented clearly.
- Next (product/app): wire cutover, back-office editor, fill coverage `coversZoneIds` and multi-slot SMS windows that were previously hard-coded.

## Related

- Requirements: [requirements.md](requirements.md)
- Legacy shape: [legacy-schema.json](legacy-schema.json)
