# Docs index

Team-facing documentation for the parking rule-data JSON format.

| Doc | Audience | Contents |
| --- | --- | --- |
| [field-reference.md](field-reference.md) | Teammates reviewing / editing | **Every field** — type, required/optional, meaning, examples |
| [delivery-manifest.md](delivery-manifest.md) | App / CDN / publish | Manifest + shared + per-city files + `forceUpdate` |
| [geojson-import.md](geojson-import.md) | Local import | GeoJSON → monolith (confidential polygons) |
| [schema.md](schema.md) | Engineers / product | Concepts: layers, inheritance, payment channels, mapping |
| [parking-config.schema.json](parking-config.schema.json) | Tooling / validation | JSON Schema |
| [project-context.md](project-context.md) | Everyone | Locked design decisions + status |
| [requirements.md](requirements.md) | Product | Functional requirements list |
| [legacy-schema.json](legacy-schema.json) | Migration reference | Old `zonesData_v2` shape |

Repo landing page: [../README.md](../README.md).  
Full generated config (monolith): [../data/parking-config.generated.json](../data/parking-config.generated.json).  
Sample delivery stub: [../examples/delivery/](../examples/delivery/).
