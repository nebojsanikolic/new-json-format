# Client-resolve fixtures

Golden inputs + expected resolved offers for [docs/client-resolve.md](../../docs/client-resolve.md).

| File | Scenario |
| --- | --- |
| `01-timed-weekday.*` | Timed zone, Wed 12:00, in window |
| `02-fullday-evening.*` | Full-day-only lot, Wed 18:00, outside window |

Apps should match `*.expected.json` fields (names/prices/rules); extra diagnostic keys OK.
