# New JSON format

Rule-data parking configuration for Nebojša Nikolić’s parking app — a clean cutover from the flat `zonesData_v2` shape.

## What’s in this repo

| Path | Purpose |
| --- | --- |
| [`data/parking-config.generated.json`](data/parking-config.generated.json) | **Main deliverable** — full production data in the new format |
| [`data/zonesData_v2.source.json`](data/zonesData_v2.source.json) | Snapshot of production input |
| [`docs/schema.md`](docs/schema.md) | Human-readable format guide |
| [`docs/parking-config.schema.json`](docs/parking-config.schema.json) | JSON Schema |
| [`docs/requirements.md`](docs/requirements.md) | Product requirements |
| [`docs/project-context.md`](docs/project-context.md) | Locked design decisions |
| [`examples/belgrade-snippet.json`](examples/belgrade-snippet.json) | Belgrade excerpt (polygons truncated) |
| [`scripts/transform.py`](scripts/transform.py) | Regenerates generated JSON from source |

## Design in one page

- **Catalog** → countries / cities / operators / currencies  
- **Geography** → zones → polygons (**polygon overrides zone**)  
- **Commerce** → products + typed rules + channel-agnostic payment methods (`sms` now, `webview_card` later)  
- Money always `{ "amount", "currencyId" }`  
- Locales as maps (cases nested under locale)  
- `dataVersion` + `minAppVersion`; unknown rule/payment types ignored by older apps  

Full detail: [`docs/schema.md`](docs/schema.md).

## Regenerate

```bash
python3 scripts/transform.py
```

Requires Python 3.10+. Reads `data/zonesData_v2.source.json`, writes the generated file and Belgrade example.

## Source data

Production input:  
https://raw.githubusercontent.com/nebojsanikolic/jsonHost/refs/heads/main/zonesData_v2.json
