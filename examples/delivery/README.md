# Example delivery package (stub)

Minimal **fake** Belgrade slice for reviewing the publish layout.
Not production data — one tiny rectangle polygon, example SMS/price.

| File | Role |
| --- | --- |
| [`manifest.json`](manifest.json) | Always fetched first; `forceUpdate: true` on Belgrade demo; `minAppVersions` + `exchangeRates` slot |
| [`shared.json`](shared.json) | Locales, currencies (no FX), countries, operators |
| [`exchange-rates.json`](exchange-rates.json) | FX vs base currency (`baseCurrencyId`, `rates`, `asOf`) |
| [`cities/city-beograd.json`](cities/city-beograd.json) | One-city slice |

Semantics: [`docs/delivery-manifest.md`](../../docs/delivery-manifest.md).
