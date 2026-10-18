# Parking data structure and requirements

Source: user list (2026-10-18). Goal: rule-data JSON that scales without force updates; fully editable in back office.

## Functional requirements

1. **Minimum app version** — data declares min app version needed to use it.
2. **Decentralized countries** — countries as array objects; easy add/remove.
3. **Multilingual countries/cities** — locales, alternative city names, grammatical cases (better organized than today).
4. **Polygon-level info** — e.g. payment hours at polygon may differ from zone; Belgrade subzones.
5. **Full-day button color** — configurable; Šabac example (24h vs end-of-day validity is related).
6. **Full-day validity mode** — end of calendar day vs 24h from purchase.
7. **Decimal prices** — explicit requirement.
8. **Per-hour price ladder** — different price for 1st, 2nd, 3rd… hour.
9. **Night rates** — different pricing in night periods.
10. **Split payment periods** — multiple windows per day (e.g. Podgorica off-street).
11. **Nth SMS send restrictions** — e.g. Belgrade 4th SMS only in last 10 min of 3rd.
12. **Zone price coverage** — expensive zone ticket may cover cheaper zones.
13. **Multi-zone overlap UX** — when location in 2+ zones: offer expensive, none, etc.; related to 12.
14. **Per-message time limits** — e.g. Belgrade Zone 1: 60 + 30 minutes.
15. **Cooldown** — block further payments after max duration reached.
16. **Seasonal / event zones** — active windows; event polygon expansion (Zaječar fair).
17. **Full-day-only zones** — zones that only sell daily tickets but still have cards, color, price, polygons; daily tickets get same config depth as regular.
18. **Seasonal pricing** — summer/winter etc.; backend may compute, format must support.
19. **Centralized operators** — for fine display etc.
20. **Fines and discounts** — amounts; discount amount/% and discount period duration.
21. **Residential zones** — resident-only rules.
22. **Resident permits** — permit info and valid zones.
23. **Coverage polygons** — city parking coverage + country geographic coverage.
24. **Scheduled effective dates** — prepare price/detail/polygon changes ahead of time.
25. **Language-specific sort order**.
26. **Exchange rates**.
27. **Per-minute pricing** — not only hourly.

## Cross-cutting

- Entire format editable via web back office: clear, self-explanatory field/object names; non-developers can configure without knowing implementation.
