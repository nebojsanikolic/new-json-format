#!/usr/bin/env python3
"""Transform legacy zonesData_v2.json into parking-config rule-data format."""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SOURCE_URL = (
    "https://raw.githubusercontent.com/nebojsanikolic/jsonHost/"
    "refs/heads/main/zonesData_v2.json"
)

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday"]
LOCALE_CATALOG = [
    {"id": "sr-Latn", "name": "Srpski (latinica)", "sortOrder": 1},
    {"id": "sr-Cyrl", "name": "Srpski (ćirilica)", "sortOrder": 2},
    {"id": "en", "name": "English", "sortOrder": 3},
    {"id": "ru", "name": "Русский", "sortOrder": 4},
]

COUNTRY_META = {
    "rs": {
        "timezone": "Europe/Belgrade",
        "defaultCurrencyId": "rsd",
        "locales": {
            "sr-Latn": {"name": "Srbija"},
            "sr-Cyrl": {"name": "Србија"},
            "en": {"name": "Serbia"},
            "ru": {"name": "Сербия"},
        },
        "languageSortOrder": ["sr-Latn", "sr-Cyrl", "en", "ru"],
    },
    "me": {
        "timezone": "Europe/Podgorica",
        "defaultCurrencyId": "eur",
        "locales": {
            "sr-Latn": {"name": "Crna Gora"},
            "sr-Cyrl": {"name": "Црна Гора"},
            "en": {"name": "Montenegro"},
            "ru": {"name": "Черногория"},
        },
        "languageSortOrder": ["sr-Latn", "sr-Cyrl", "en", "ru"],
    },
}


def slugify(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = "".join(c for c in normalized if not unicodedata.combining(c))
    ascii_text = ascii_text.lower()
    ascii_text = re.sub(r"[^a-z0-9]+", "-", ascii_text)
    return ascii_text.strip("-") or "item"


def currency_id_from_code(code: str) -> str:
    return code.strip().lower()


def resolve_currency_id(
    raw: dict[str, Any],
    currency_by_legacy: dict[int, str],
    currency_by_code: dict[str, str],
    country_default: str,
) -> str:
    if raw.get("currency_id") is not None:
        legacy = int(raw["currency_id"])
        if legacy in currency_by_legacy:
            return currency_by_legacy[legacy]
    code = (raw.get("currency") or "").strip()
    if code:
        key = code.upper()
        if key in currency_by_code:
            return currency_by_code[key]
        return currency_id_from_code(code)
    return country_default


def hour_to_hhmm(value: Any) -> str:
    """Convert legacy hour number (7, 7.5, 24) to HH:mm. Supports end-of-day 24:00."""
    if isinstance(value, str) and ":" in value:
        return value
    n = float(value)
    if n >= 24:
        return "24:00"
    if n < 0:
        n = 0.0
    hours = int(n)
    minutes = int(round((n - hours) * 60))
    if minutes == 60:
        hours += 1
        minutes = 0
    if hours >= 24:
        return "24:00"
    return f"{hours:02d}:{minutes:02d}"


def round_coord(value: Any) -> float:
    """Store lat/lng with exactly 6 decimal places (as a number)."""
    return round(float(value), 6)


def lat_lng(latitude: Any, longitude: Any) -> list[float]:
    """Storage point as [lat, lon] (lat-first; not GeoJSON order)."""
    return [round_coord(latitude), round_coord(longitude)]


def payment_windows_from_hours(parking_hours: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not parking_hours:
        return []
    windows: list[dict[str, Any]] = []

    def add(days: list[str], block: dict[str, Any] | None) -> None:
        if not block:
            return
        start, end = block.get("start"), block.get("end")
        if start is None or end is None:
            return
        windows.append(
            {
                "days": days,
                "startHour": hour_to_hhmm(start),
                "endHour": hour_to_hhmm(end),
            }
        )

    add(WEEKDAYS, parking_hours.get("weekday"))
    add(["saturday"], parking_hours.get("saturday"))
    add(["sunday"], parking_hours.get("sunday"))
    return windows


def infer_full_day_validity(desc_blob: str) -> str:
    text = (desc_blob or "").lower()
    if "24" in text and ("hour" in text or "sat" in text or "čas" in text or "cas" in text):
        return "rolling_24h"
    # Šabac / most Serbian dailies: valid until end of payment period that day
    return "calendar_day"


def build_currencies(raw_list: list[dict[str, Any]]) -> tuple[list[dict], dict[int, str], dict[str, str]]:
    currencies = []
    by_legacy: dict[int, str] = {}
    by_code: dict[str, str] = {}
    for item in raw_list:
        cid = currency_id_from_code(item["code"])
        entry = {
            "id": cid,
            "legacyId": item.get("id"),
            "code": item["code"],
            "symbol": item.get("symbol") or item["code"],
            "exchangeRate": float(item.get("exchangeRate") or 1),
            "locales": {
                "en": {"name": item.get("name") or item["code"]},
            },
        }
        currencies.append(entry)
        if item.get("id") is not None:
            by_legacy[int(item["id"])] = cid
        by_code[item["code"].upper()] = cid
    return currencies, by_legacy, by_code


def city_locales(raw: dict[str, Any]) -> dict[str, Any]:
    sr: dict[str, Any] = {"name": raw.get("city_name") or ""}
    if raw.get("city_name_preposition"):
        sr["preposition"] = raw["city_name_preposition"]
    cases = {}
    for case, key in [
        ("genitive", "city_name_genitive"),
        ("dative", "city_name_dative"),
        ("accusative", "city_name_accusative"),
        ("locative", "city_name_locative"),
        ("instrumental", "city_name_instrumental"),
    ]:
        if raw.get(key):
            cases[case] = raw[key]
    if cases:
        sr["cases"] = cases
    locales: dict[str, Any] = {"sr-Latn": sr}
    if raw.get("city_name_ru"):
        locales["ru"] = {"name": raw["city_name_ru"]}
    # English fallback = Latin name (legacy had no city_name_en)
    locales["en"] = {"name": raw.get("city_name") or ""}
    return locales


def zone_locales(raw: dict[str, Any]) -> dict[str, Any]:
    locales: dict[str, Any] = {
        "sr-Latn": {
            "name": raw.get("name") or "",
            "description": raw.get("description") or "",
        },
        "sr-Cyrl": {
            "name": raw.get("name_rs_cyrl") or raw.get("name") or "",
            "description": raw.get("description_rs_cyrl") or "",
        },
        "en": {
            "name": raw.get("name_en") or raw.get("name") or "",
            "description": raw.get("description_en") or "",
        },
        "ru": {
            "name": raw.get("name_ru") or "",
            "description": raw.get("description_ru") or "",
        },
    }
    info = raw.get("info_note") or {}
    if info.get("rs"):
        locales["sr-Latn"]["infoNote"] = info["rs"]
    if info.get("en"):
        locales["en"]["infoNote"] = info["en"]
    if info.get("ru"):
        locales["ru"]["infoNote"] = info["ru"]
    return locales


def daily_locales(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "sr-Latn": {
            "name": raw.get("name") or "",
            "description": raw.get("desc") or "",
        },
        "sr-Cyrl": {
            "name": raw.get("name_rs_cyrl") or "",
            "description": raw.get("desc_rs_cyrl") or "",
        },
        "en": {
            "name": raw.get("name_en") or "",
            "description": raw.get("desc_en") or "",
        },
        "ru": {
            "name": raw.get("name_ru") or "",
            "description": raw.get("desc_ru") or "",
        },
    }


def transform(source: dict[str, Any]) -> dict[str, Any]:
    currencies, currency_by_legacy, currency_by_code = build_currencies(source.get("currency") or [])

    countries = []
    for cid, meta in COUNTRY_META.items():
        countries.append(
            {
                "id": cid,
                "timezone": meta["timezone"],
                "defaultCurrencyId": meta["defaultCurrencyId"],
                "languageSortOrder": meta["languageSortOrder"],
                "locales": meta["locales"],
                "coveragePolygon": None,
                "effectiveFrom": None,
                "effectiveTo": None,
            }
        )

    cities_out: list[dict[str, Any]] = []
    zones_out: list[dict[str, Any]] = []
    polygons_out: list[dict[str, Any]] = []
    products_out: list[dict[str, Any]] = []
    payment_methods_out: list[dict[str, Any]] = []
    rules_out: list[dict[str, Any]] = []
    coverage_policies: list[dict[str, Any]] = []

    # Disabled structural example for future card payments
    payment_methods_out.append(
        {
            "id": "pay-webview-card-example",
            "type": "webview_card",
            "enabled": False,
            "webviewCard": {
                "urlTemplate": (
                    "https://pay.example.com/checkout"
                    "?zone={zoneId}&product={productId}&plate={plate}"
                ),
                "returnUrlScheme": "parkingapp://payment-result",
                "parameters": {},
            },
            "effectiveFrom": None,
            "effectiveTo": None,
        }
    )

    legacy_zone_to_new: dict[int, str] = {}
    used_ids: set[str] = set()

    def unique(base: str) -> str:
        if base not in used_ids:
            used_ids.add(base)
            return base
        i = 2
        while f"{base}-{i}" in used_ids:
            i += 1
        final = f"{base}-{i}"
        used_ids.add(final)
        return final

    country_batches = [
        ("rs", source.get("cities") or []),
        ("me", source.get("montenegro_cities") or []),
    ]

    for country_id, city_list in country_batches:
        country_default_currency = COUNTRY_META[country_id]["defaultCurrencyId"]
        country_tz = COUNTRY_META[country_id]["timezone"]

        for raw_city in city_list:
            city_slug = slugify(raw_city.get("city_name") or f"city-{raw_city.get('city_id')}")
            city_id = unique(f"city-{city_slug}")
            zone_ids: list[str] = []
            coverage_zone_entries: list[dict[str, Any]] = []
            full_day_colors: list[str] = []

            # First pass: create zones + timed products so daily tickets can resolve forZones
            pending_dailies = list(raw_city.get("daily_tickets") or [])
            zone_price_for_rank: dict[str, float] = {}

            for raw_zone in raw_city.get("Zones") or []:
                z_legacy = int(raw_zone["id"])
                z_slug = slugify(raw_zone.get("name") or str(z_legacy))
                zone_id = unique(f"zone-{city_slug}-{z_slug}")
                legacy_zone_to_new[z_legacy] = zone_id
                zone_ids.append(zone_id)

                currency_id = resolve_currency_id(
                    raw_zone, currency_by_legacy, currency_by_code, country_default_currency
                )
                duration = int(raw_zone.get("value") or 60)
                price_amount = float(raw_zone.get("price") or 0)
                zone_price_for_rank[zone_id] = price_amount

                # Polygons
                polygon_ids: list[str] = []
                for idx, ring in enumerate(raw_zone.get("coordinates") or []):
                    poly_id = unique(f"poly-{city_slug}-{z_slug}-{idx}")
                    polygon_ids.append(poly_id)
                    polygons_out.append(
                        {
                            "id": poly_id,
                            "zoneId": zone_id,
                            "enabled": True,
                            "coordinates": [
                                lat_lng(p["latitude"], p["longitude"]) for p in ring
                            ],
                            "overrides": {},
                            "effectiveFrom": None,
                            "effectiveTo": None,
                        }
                    )

                # SMS payment method
                pay_id = unique(f"pay-sms-{city_slug}-{z_slug}")
                max_minutes = None
                cooldown = None
                rule_ids: list[str] = []
                if raw_zone.get("restriction") and raw_zone.get("restriction_time"):
                    max_minutes = int(raw_zone["restriction_time"])
                    rule_max_id = unique(f"rule-max-duration-{city_slug}-{z_slug}")
                    rules_out.append(
                        {
                            "id": rule_max_id,
                            "type": "max_duration",
                            "maxDurationMinutes": max_minutes,
                            "notes": "Mapped from legacy restriction_time",
                        }
                    )
                    rule_ids.append(rule_max_id)
                    cooldown = {
                        "enabled": True,
                        "resumeNextPaymentWindow": True,
                    }
                    rule_cd_id = unique(f"rule-cooldown-{city_slug}-{z_slug}")
                    rules_out.append(
                        {
                            "id": rule_cd_id,
                            "type": "cooldown_after_max",
                            "enabled": True,
                            "resumeNextPaymentWindow": True,
                            "notes": "Inferred: block further SMS after max duration until next payment window",
                        }
                    )
                    rule_ids.append(rule_cd_id)

                payment_methods_out.append(
                    {
                        "id": pay_id,
                        "type": "sms",
                        "enabled": True,
                        "sms": {
                            "number": str(raw_zone.get("sms_number") or ""),
                            "prefix": str(raw_zone.get("sms_prefix") or ""),
                            "messageSlots": [
                                {
                                    "index": 1,
                                    "durationMinutes": duration,
                                    "sendWindow": None,
                                }
                            ],
                            "maxDurationMinutes": max_minutes,
                            "cooldownAfterMax": cooldown,
                        },
                        "effectiveFrom": None,
                        "effectiveTo": None,
                    }
                )

                # Timed product
                pricing_mode = "per_hour" if raw_zone.get("per_hour", True) else "fixed"
                # Support per-minute when duration unit is 1 minute (none in prod, but mode exists)
                if duration == 1:
                    pricing_mode = "per_minute"

                prod_id = unique(f"prod-timed-{city_slug}-{z_slug}")
                products_out.append(
                    {
                        "id": prod_id,
                        "legacyId": z_legacy,
                        "kind": "timed",
                        "zoneIds": [zone_id],
                        "coversZoneIds": [],
                        "locales": zone_locales(raw_zone),
                        "color": raw_zone.get("color"),
                        "price": {"amount": price_amount, "currencyId": currency_id},
                        "pricing": {
                            "mode": pricing_mode,
                            "baseDurationMinutes": duration,
                            "ladder": [],
                            "nightRates": [],
                            "seasonalPrices": [],
                        },
                        "validity": {
                            "mode": None,
                            "durationMinutes": duration,
                            "buttonColor": None,
                        },
                        "paymentMethodIds": [pay_id],
                        "ruleIds": rule_ids,
                        "eligibility": {"type": "public"},
                        "effectiveFrom": None,
                        "effectiveTo": None,
                    }
                )

                zones_out.append(
                    {
                        "id": zone_id,
                        "legacyId": z_legacy,
                        "cityId": city_id,
                        "enabled": True,
                        "color": raw_zone.get("color") or "#888888",
                        "locales": zone_locales(raw_zone),
                        "polygonIds": polygon_ids,
                        "productIds": [prod_id],  # dailies appended later
                        "paymentMethodIds": [pay_id],
                        "paymentWindows": payment_windows_from_hours(raw_zone.get("parking_hours")),
                        "workingDayOverrides": list(raw_zone.get("working_days_override") or []),
                        "eligibility": {"type": "public"},
                        "fullDayOnly": False,
                        "seasonalWindows": [],
                        "operatorId": None,
                        "effectiveFrom": None,
                        "effectiveTo": None,
                    }
                )

            # Daily tickets
            zone_by_id = {z["id"]: z for z in zones_out if z["cityId"] == city_id}
            for raw_daily in pending_dailies:
                d_legacy = raw_daily.get("parking_zone_id")
                d_name = raw_daily.get("name") or f"daily-{d_legacy}"
                d_slug = slugify(d_name)
                prod_id = unique(f"prod-fullday-{city_slug}-{d_slug}")

                target_zone_ids: list[str] = []
                for fz in raw_daily.get("forZones") or []:
                    mapped = legacy_zone_to_new.get(int(fz))
                    if mapped:
                        target_zone_ids.append(mapped)

                currency_id = resolve_currency_id(
                    raw_daily, currency_by_legacy, currency_by_code, country_default_currency
                )
                prefix = raw_daily.get("sms_prefix_daily")
                if prefix is None:
                    prefix = raw_daily.get("sms_prefix") or ""

                pay_id = unique(f"pay-sms-fullday-{city_slug}-{d_slug}")
                interval = int(raw_daily.get("interval") or 1440)
                desc_blob = " ".join(
                    filter(
                        None,
                        [
                            raw_daily.get("desc"),
                            raw_daily.get("desc_en"),
                        ],
                    )
                )
                validity_mode = infer_full_day_validity(desc_blob)
                color = raw_daily.get("color")
                if color:
                    full_day_colors.append(color)

                payment_methods_out.append(
                    {
                        "id": pay_id,
                        "type": "sms",
                        "enabled": True,
                        "sms": {
                            "number": str(raw_daily.get("sms_number") or ""),
                            "prefix": str(prefix),
                            "messageSlots": [
                                {
                                    "index": 1,
                                    "durationMinutes": interval,
                                    "sendWindow": None,
                                }
                            ],
                            "maxDurationMinutes": interval,
                            "cooldownAfterMax": None,
                        },
                        "effectiveFrom": None,
                        "effectiveTo": None,
                    }
                )

                products_out.append(
                    {
                        "id": prod_id,
                        "legacyId": int(d_legacy) if d_legacy is not None else None,
                        "kind": "full_day",
                        "zoneIds": target_zone_ids,
                        "coversZoneIds": [],
                        "locales": daily_locales(raw_daily),
                        "color": color,
                        "price": {
                            "amount": float(raw_daily.get("price") or 0),
                            "currencyId": currency_id,
                        },
                        "pricing": {
                            "mode": "fixed",
                            "baseDurationMinutes": interval,
                            "ladder": [],
                            "nightRates": [],
                            "seasonalPrices": [],
                        },
                        "validity": {
                            "mode": validity_mode,
                            "durationMinutes": interval,
                            "buttonColor": color,
                        },
                        "paymentMethodIds": [pay_id],
                        "ruleIds": [],
                        "eligibility": {"type": "public"},
                        "effectiveFrom": None,
                        "effectiveTo": None,
                    }
                )

                for zid in target_zone_ids:
                    z = zone_by_id.get(zid)
                    if z is not None:
                        z["productIds"].append(prod_id)
                        if pay_id not in z["paymentMethodIds"]:
                            z["paymentMethodIds"].append(pay_id)

            # Mark fullDayOnly when zone has only full_day products
            for zid in zone_ids:
                z = zone_by_id[zid]
                kinds = []
                for pid in z["productIds"]:
                    for p in products_out:
                        if p["id"] == pid:
                            kinds.append(p["kind"])
                            break
                if kinds and all(k == "full_day" for k in kinds):
                    z["fullDayOnly"] = True

            # Coverage policy: rank by price (higher price = higher rank)
            ranked = sorted(
                zone_price_for_rank.items(),
                key=lambda kv: kv[1],
                reverse=True,
            )
            for rank_index, (zid, price) in enumerate(ranked):
                coverage_zone_entries.append(
                    {
                        "zoneId": zid,
                        "rank": int(round(price * 1000)) + (len(ranked) - rank_index),
                        "coversZoneIds": [],
                    }
                )

            policy_id = None
            if coverage_zone_entries:
                policy_id = unique(f"coverage-{city_slug}")
                coverage_policies.append(
                    {
                        "id": policy_id,
                        "cityId": city_id,
                        "onOverlap": "offer_highest_rank",
                        "zones": coverage_zone_entries,
                    }
                )

            center = raw_city.get("city_coordinate") or {}
            cities_out.append(
                {
                    "id": city_id,
                    "legacyId": raw_city.get("city_id"),
                    "countryId": country_id,
                    "timezone": country_tz,
                    "shortName": raw_city.get("city_short_name") or "",
                    "center": lat_lng(
                        center.get("latitude") or 0,
                        center.get("longitude") or 0,
                    ),
                    "locales": city_locales(raw_city),
                    "zoneIds": zone_ids,
                    "coveragePolicyId": policy_id,
                    "coveragePolygon": None,
                    "fullDayButtonColor": full_day_colors[0] if full_day_colors else None,
                    "effectiveFrom": None,
                    "effectiveTo": None,
                }
            )

    return {
        "dataVersion": "1.0.0",
        "minAppVersion": "5.0.0",
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": {
            "url": SOURCE_URL,
            "legacyVersion": source.get("version"),
            "notes": (
                "Transformed from production zonesData_v2. "
                "Empty arrays (operators, residentPermits, fines) and empty "
                "Empty pricing.ladder[] (use stepIndex+durationMinutes+price when filled), "
                "nightRates/seasonalWindows are intentional hooks. "
                "pay-webview-card-example is disabled structural sample."
            ),
        },
        "locales": LOCALE_CATALOG,
        "currencies": currencies,
        "countries": countries,
        "operators": [],
        "cities": cities_out,
        "zones": zones_out,
        "polygons": polygons_out,
        "products": products_out,
        "paymentMethods": payment_methods_out,
        "rules": rules_out,
        "coveragePolicies": coverage_policies,
        "residentPermits": [],
        "fines": [],
    }


def belgrade_snippet(config: dict[str, Any]) -> dict[str, Any]:
    """Small readable excerpt: Belgrade without full polygon rings."""
    city = next(c for c in config["cities"] if c["legacyId"] == 11)
    zone_ids = set(city["zoneIds"])
    zones = []
    for z in config["zones"]:
        if z["id"] not in zone_ids:
            continue
        z_copy = dict(z)
        z_copy["polygonIds"] = z_copy["polygonIds"][:1]
        z_copy["_polygonCount"] = len(z["polygonIds"])
        zones.append(z_copy)

    polygon_ids = {z["polygonIds"][0] for z in zones if z["polygonIds"]}
    polygons = []
    for p in config["polygons"]:
        if p["id"] in polygon_ids:
            ring = p["coordinates"]
            clipped = {**p, "coordinates": ring[:3] if len(ring) > 3 else list(ring)}
            clipped.pop("_ringPointCount", None)
            polygons.append(clipped)

    product_ids = {pid for z in zones for pid in z["productIds"]}
    products = [p for p in config["products"] if p["id"] in product_ids]
    pay_ids = {pid for p in products for pid in p["paymentMethodIds"]}
    pays = [p for p in config["paymentMethods"] if p["id"] in pay_ids or p["id"] == "pay-webview-card-example"]
    rule_ids = {rid for p in products for rid in p["ruleIds"]}
    rules = [r for r in config["rules"] if r["id"] in rule_ids]
    policy = next(
        (c for c in config["coveragePolicies"] if c["cityId"] == city["id"]),
        None,
    )

    return {
        "dataVersion": config["dataVersion"],
        "minAppVersion": config["minAppVersion"],
        "note": "Belgrade excerpt — polygons truncated for readability; see parking-config.generated.json for full data.",
        "city": city,
        "zones": zones,
        "polygons": polygons,
        "products": products,
        "paymentMethods": pays,
        "rules": rules,
        "coveragePolicy": policy,
        "currencies": [c for c in config["currencies"] if c["id"] in ("rsd", "eur")],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("data/zonesData_v2.source.json"),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("data/parking-config.generated.json"),
    )
    parser.add_argument(
        "--snippet",
        type=Path,
        default=Path("examples/belgrade-snippet.json"),
    )
    args = parser.parse_args()

    source = json.loads(args.source.read_text(encoding="utf-8"))
    config = transform(source)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    snippet = belgrade_snippet(config)
    args.snippet.parent.mkdir(parents=True, exist_ok=True)
    args.snippet.write_text(
        json.dumps(snippet, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "cities": len(config["cities"]),
                "zones": len(config["zones"]),
                "polygons": len(config["polygons"]),
                "products": len(config["products"]),
                "paymentMethods": len(config["paymentMethods"]),
                "rules": len(config["rules"]),
                "coveragePolicies": len(config["coveragePolicies"]),
                "outBytes": args.out.stat().st_size,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
