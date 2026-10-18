# New JSON format

Rule-data parking configuration for Nebojša Nikolić’s parking app.

This repo defines a **new remote-config JSON shape** to replace today’s flat `zonesData_v2` file. After one cutover (force-update is OK), new parking rules can ship via config without hard-coding them in the app — except brand-new engine capabilities that need a newer app version.

There is **no legacy-format compatibility**. Field names are written for a back-office editor (non-developers), not for matching old keys.

## Start here

| Read this | For |
| --- | --- |
| [`docs/field-reference.md`](docs/field-reference.md) | **Full field reference** — every parameter for teammates |
| [`docs/schema.md`](docs/schema.md) | Concept guide (layers, inheritance, mapping) |
| [`docs/parking-config.schema.json`](docs/parking-config.schema.json) | Machine JSON Schema |
| [`data/parking-config.generated.json`](data/parking-config.generated.json) | **Full transformed production data** (main deliverable) |
| [`examples/belgrade-snippet.json`](examples/belgrade-snippet.json) | Small Belgrade excerpt (polygons truncated) |
| [`docs/project-context.md`](docs/project-context.md) | Locked design decisions |
| [`docs/requirements.md`](docs/requirements.md) | Product requirements list |

## Architecture (three layers)

```
catalog      countries · cities · operators · currencies · locales
geography    zones → polygons     (polygon.overrides.* beats the zone)
commerce     products + rules + paymentMethods
```

- **Products** describe *what* is sold (duration, price, eligibility, validity).
- **Payment methods** describe *how* to pay, by `type`:
  - `sms` — live today (number, prefix, `messageSlots`, send windows, cooldown)
  - `webview_card` — ready structurally; add a method + app support later **without reshaping** products or zones
- **Money** is always `{ "amount": number, "currencyId": string }`.
- **Locales** are maps (`sr-Latn`, `en`, …); grammatical cases nest under the locale.
- **Versioning:** `dataVersion` (cache freshness) + `minAppVersion`. Unknown rule/payment `type` values are ignored by older apps.

## Repo layout

```
README.md
data/
  parking-config.generated.json   # full new-format config from production
  zonesData_v2.source.json        # snapshot of production input
docs/
  schema.md                       # format guide
  parking-config.schema.json      # JSON Schema
  project-context.md              # decisions
  requirements.md
  legacy-schema.json              # old shape (reference only)
examples/
  belgrade-snippet.json
scripts/
  transform.py                    # regenerates generated JSON + Belgrade example
```

## How the generated file was produced

1. Production source:  
   https://raw.githubusercontent.com/nebojsanikolic/jsonHost/refs/heads/main/zonesData_v2.json  
   (snapshot also stored as `data/zonesData_v2.source.json`)
2. Transform: `python3 scripts/transform.py`
3. Output: `data/parking-config.generated.json`  
   (~98 cities, 211 zones, polygons, timed + full-day products, SMS payment methods, coverage policy stubs)

Features not present in production (night rates, price ladders, seasonal overlays, resident permits, fines, live webview card, explicit `coversZoneIds`) are **hooks in the schema** — empty arrays, disabled example payment method, or documented for back office to fill.

## Regenerate locally

```bash
python3 scripts/transform.py
```

Python 3.10+. Overwrites `data/parking-config.generated.json` and `examples/belgrade-snippet.json`.

## Review tips

1. Architecture overview above → then [`docs/field-reference.md`](docs/field-reference.md) for every field.
2. Open [`examples/belgrade-snippet.json`](examples/belgrade-snippet.json) for a readable city.
3. Spot-check the full file against [`docs/parking-config.schema.json`](docs/parking-config.schema.json).
4. Concepts + production mapping: [`docs/schema.md`](docs/schema.md); legacy shape: [`docs/legacy-schema.json`](docs/legacy-schema.json).
