# Example delivery package (stub)

Minimal **fake** Belgrade slice for reviewing the publish layout.
Not production data — one tiny rectangle polygon, example SMS/price.

| File | Role |
| --- | --- |
| [`manifest.json`](manifest.json) | Always fetched first; `forceUpdate: true` on Belgrade demo |
| [`shared.json`](shared.json) | Locales, currencies, countries, operators |
| [`cities/city-beograd.json`](cities/city-beograd.json) | One-city slice |

Semantics: [`docs/delivery-manifest.md`](../../docs/delivery-manifest.md).
