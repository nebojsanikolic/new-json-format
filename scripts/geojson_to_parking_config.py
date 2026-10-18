#!/usr/bin/env python3
"""Convert parking-zone GeoJSON FeatureCollections into parking-config format.

Designed for local confidential GeoJSON sources (Serbia + Montenegro).
Does not fetch or commit GeoJSON — pass local paths via CLI.

See docs/geojson-import.md for property mapping and run instructions.
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday"]
ALL_DAYS = WEEKDAYS + ["saturday", "sunday"]

DAY_ALIAS = {
    "mo": "monday",
    "tu": "tuesday",
    "we": "wednesday",
    "th": "thursday",
    "fr": "friday",
    "sa": "saturday",
    "su": "sunday",
}
DAY_ORDER = {d: i for i, d in enumerate(ALL_DAYS)}

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

CURRENCY_SEED = [
    {
        "id": "rsd",
        "legacyId": 1,
        "code": "RSD",
        "symbol": "RSD",
        "exchangeRate": 1.0,
        "locales": {"en": {"name": "Serbian Dinar"}},
    },
    {
        "id": "eur",
        "legacyId": 2,
        "code": "EUR",
        "symbol": "€",
        "exchangeRate": 117.0,
        "locales": {"en": {"name": "Euro"}},
    },
]

MONEY_RE = re.compile(
    r"^\s*(?P<amount>\d+(?:[.,]\d+)?)\s*(?P<code>[A-Za-z€$]*)?\s*$"
)
DURATION_RE = re.compile(r"^\s*(?P<n>\d+)\s*minutes?\s*$", re.I)
FEE_CHUNK_RE = re.compile(
    r"yes\s*@\s*(?P<days>[A-Za-z\-]+)\s+(?P<start>\d{1,2}:\d{2})\s*-\s*(?P<end>\d{1,2}:\d{2})",
    re.I,
)
PERCENT_RE = re.compile(r"(?P<p>\d+)\s*%")


def slugify(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text or "")
    ascii_text = "".join(c for c in normalized if not unicodedata.combining(c))
    ascii_text = ascii_text.lower()
    ascii_text = re.sub(r"[^a-z0-9]+", "-", ascii_text)
    return ascii_text.strip("-") or "item"


def round_coord(value: Any) -> float:
    return round(float(value), 6)


def lat_lng(latitude: Any, longitude: Any) -> dict[str, float]:
    return {"latitude": round_coord(latitude), "longitude": round_coord(longitude)}


def normalize_hhmm(value: str) -> str:
    parts = value.strip().split(":")
    h = int(parts[0])
    m = int(parts[1]) if len(parts) > 1 else 0
    if h >= 24:
        return "24:00"
    return f"{h:02d}:{m:02d}"


def parse_money(
    raw: Any, default_currency_id: str
) -> dict[str, Any] | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text or text.upper() in {"N/A", "NA", "NONE", "-"}:
        return None
    # e.g. "2.50 EUR/h" → take leading money token
    text = re.split(r"[/\s]+per", text, maxsplit=1, flags=re.I)[0]
    text = text.split("/")[0].strip()
    m = MONEY_RE.match(text)
    if not m:
        return None
    amount = float(m.group("amount").replace(",", "."))
    code = (m.group("code") or "").strip().upper().replace("€", "EUR")
    if code in {"", "DIN", "DINARA"}:
        currency_id = default_currency_id
    else:
        currency_id = code.lower()
    return {"amount": amount, "currencyId": currency_id}


def parse_duration_minutes(raw: Any) -> int | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text or text.lower() in {"no", "n/a", "none", "-"}:
        return None
    m = DURATION_RE.match(text)
    if not m:
        return None
    return int(m.group("n"))


def clean_sms_prefix(raw: Any) -> str:
    if raw is None:
        return ""
    text = str(raw).strip()
    # GeoJSON sometimes stores quoted prefixes like: "1 "
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {'"', "'"}:
        text = text[1:-1]
    return text


def expand_day_token(token: str) -> list[str]:
    token = token.strip().lower()
    if "-" in token:
        start_s, end_s = token.split("-", 1)
        start = DAY_ALIAS.get(start_s[:2])
        end = DAY_ALIAS.get(end_s[:2])
        if start is None or end is None:
            return []
        i0, i1 = DAY_ORDER[start], DAY_ORDER[end]
        if i0 <= i1:
            return ALL_DAYS[i0 : i1 + 1]
        return ALL_DAYS[i0:] + ALL_DAYS[: i1 + 1]
    day = DAY_ALIAS.get(token[:2])
    return [day] if day else []


def parse_fee_conditional(raw: Any) -> list[dict[str, Any]]:
    if not raw:
        return []
    text = str(raw)
    windows: list[dict[str, Any]] = []
    for m in FEE_CHUNK_RE.finditer(text):
        days = expand_day_token(m.group("days"))
        if not days:
            continue
        windows.append(
            {
                "days": days,
                "startHour": normalize_hhmm(m.group("start")),
                "endHour": normalize_hhmm(m.group("end")),
            }
        )
    return windows


def parse_city_center(raw: Any) -> dict[str, float] | None:
    if not raw:
        return None
    parts = [p.strip() for p in str(raw).split(",")]
    if len(parts) < 2:
        return None
    return lat_lng(parts[0], parts[1])


def ring_from_geometry(geometry: dict[str, Any] | None) -> list[dict[str, float]]:
    if not geometry:
        return []
    gtype = geometry.get("type")
    coords = geometry.get("coordinates")
    if gtype == "Polygon" and coords:
        outer = coords[0]
    elif gtype == "MultiPolygon" and coords:
        outer = coords[0][0]
    else:
        return []
    ring: list[dict[str, float]] = []
    for pt in outer:
        if len(pt) < 2:
            continue
        # GeoJSON is [lng, lat]
        ring.append(lat_lng(pt[1], pt[0]))
    return ring


def zone_locales_from_props(props: dict[str, Any]) -> dict[str, Any]:
    locales: dict[str, Any] = {}

    def put(locale: str, name_key: str, desc_key: str, note_key: str | None = None) -> None:
        name = props.get(name_key)
        desc = props.get(desc_key)
        note = props.get(note_key) if note_key else None
        if not name and not desc and not note:
            return
        entry: dict[str, Any] = {}
        if name:
            entry["name"] = str(name)
        if desc:
            entry["description"] = str(desc)
        if note:
            entry["infoNote"] = str(note)
        locales[locale] = entry

    put(
        "sr-Latn",
        "parkingzone_name:sr-Latn-RS",
        "description_zone:sr-Latn-RS",
        "info_note:sr-Latn",
    )
    put(
        "sr-Cyrl",
        "parkingzone_name:sr-Cyrl-RS",
        "description_zone:sr-Cyrl-RS",
        None,
    )
    put("en", "parkingzone_name:en-US", "description_zone:en-US", "info_note:en")
    put("ru", "parkingzone_name:ru-RU", "description_zone:ru-RU", "info_note:ru")
    if props.get("parkingzone_name:sk-SK"):
        locales["sk"] = {"name": str(props["parkingzone_name:sk-SK"])}
    if props.get("parkingzone_name:hu-HU"):
        locales["hu"] = {"name": str(props["parkingzone_name:hu-HU"])}
    # Prefer info_rate:en as English note when info_note:en missing
    if "en" in locales and "infoNote" not in locales["en"] and props.get("info_rate:en"):
        locales["en"]["infoNote"] = str(props["info_rate:en"])
    return locales


def city_locales_from_props(props: dict[str, Any]) -> dict[str, Any]:
    name = str(props.get("is_in") or "")
    locales: dict[str, Any] = {
        "sr-Latn": {"name": name},
        "en": {"name": name},
    }
    ru = props.get("is_in:ru-RU") or props.get("city_name_ru")
    if ru:
        locales["ru"] = {"name": str(ru)}
    return locales


def infer_full_day_validity(props: dict[str, Any]) -> str:
    blob = " ".join(
        str(props.get(k) or "")
        for k in (
            "info_note:en",
            "info_note:sr-Latn",
            "info_note:ru",
            "description_zone:en-US",
            "description_zone:sr-Latn-RS",
        )
    ).lower()
    if "24" in blob and (
        "hour" in blob or "sat" in blob or "čas" in blob or "cas" in blob
    ):
        return "rolling_24h"
    return "calendar_day"


def load_feature_collection(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if data.get("type") != "FeatureCollection":
        raise ValueError(f"{path}: expected FeatureCollection, got {data.get('type')}")
    return list(data.get("features") or [])


class IdFactory:
    def __init__(self) -> None:
        self._used: set[str] = set()

    def unique(self, base: str) -> str:
        if base not in self._used:
            self._used.add(base)
            return base
        i = 2
        while f"{base}-{i}" in self._used:
            i += 1
        final = f"{base}-{i}"
        self._used.add(final)
        return final


def build_ladder(
    props: dict[str, Any], default_currency_id: str
) -> tuple[str, int | None, list[dict[str, Any]], dict[str, Any] | None]:
    """Return (mode, baseDurationMinutes, ladder, base_price_money)."""
    base_price = parse_money(props.get("base_rate"), default_currency_id)
    base_mins = parse_duration_minutes(props.get("base_unit")) or 60
    steps: list[dict[str, Any]] = []

    def add_step(rate_raw: Any, unit_raw: Any, fallback_mins: int) -> None:
        money = parse_money(rate_raw, default_currency_id)
        if money is None:
            return
        mins = parse_duration_minutes(unit_raw) or fallback_mins
        steps.append(
            {
                "stepIndex": len(steps) + 1,
                "durationMinutes": mins,
                "price": money,
            }
        )

    add_step(props.get("base_rate"), props.get("base_unit"), base_mins)
    add_step(props.get("extension_rate"), props.get("extension_unit"), 60)
    add_step(props.get("extension_rate_2"), props.get("extension_unit_2"), 60)
    add_step(
        props.get("special_extension_rate"),
        props.get("special_extension_time"),
        60,
    )

    if len(steps) > 1:
        return "ladder", None, steps, base_price
    if base_price is None:
        return "per_hour", base_mins, [], None
    if base_mins == 1:
        return "per_minute", base_mins, [], base_price
    return "per_hour", base_mins, [], base_price


def message_slots_from_ladder(
    mode: str, base_mins: int | None, ladder: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    if mode == "ladder" and ladder:
        return [
            {
                "index": step["stepIndex"],
                "durationMinutes": step["durationMinutes"],
                "sendWindow": None,
            }
            for step in ladder
        ]
    duration = base_mins or 60
    return [{"index": 1, "durationMinutes": duration, "sendWindow": None}]


def transform_geojson_files(
    inputs: list[tuple[Path, str]],
    *,
    data_version: str = "1.0.0-geojson",
    min_app_version: str = "5.0.0",
) -> dict[str, Any]:
    ids = IdFactory()
    operators_by_key: dict[str, dict[str, Any]] = {}
    cities_out: list[dict[str, Any]] = []
    zones_out: list[dict[str, Any]] = []
    polygons_out: list[dict[str, Any]] = []
    products_out: list[dict[str, Any]] = []
    payment_methods_out: list[dict[str, Any]] = []
    rules_out: list[dict[str, Any]] = []
    coverage_policies: list[dict[str, Any]] = []
    fines_out: list[dict[str, Any]] = []

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

    source_notes: list[str] = []

    for path, country_id in inputs:
        source_notes.append(f"{path.name} → country {country_id}")
        features = load_feature_collection(path)
        meta = COUNTRY_META[country_id]
        default_currency = meta["defaultCurrencyId"]
        tz = meta["timezone"]

        # Group: city_id → zone_key → list of features
        by_city: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(
            lambda: defaultdict(list)
        )
        city_props: dict[str, dict[str, Any]] = {}

        for feat in features:
            props = feat.get("properties") or {}
            city_key = str(props.get("city_id") or slugify(str(props.get("is_in") or "unknown")))
            city_props.setdefault(city_key, props)
            zone_legacy = props.get("zone_id")
            if zone_legacy is None or str(zone_legacy).strip() == "":
                zone_key = f"synth-{slugify(str(props.get('parkingzone_name:sr-Latn-RS') or props.get('polygon_id') or 'zone'))}"
            else:
                zone_key = str(zone_legacy)
            by_city[city_key][zone_key].append(feat)

        for city_key, zones_map in sorted(by_city.items(), key=lambda kv: kv[0]):
            sample = city_props[city_key]
            city_name = str(sample.get("is_in") or f"city-{city_key}")
            city_slug = slugify(city_name)
            city_id = ids.unique(f"city-{city_slug}")
            try:
                legacy_city_id = int(city_key)
            except (TypeError, ValueError):
                legacy_city_id = None

            center = parse_city_center(sample.get("city_coordinate")) or {
                "latitude": 0.0,
                "longitude": 0.0,
            }

            zone_ids: list[str] = []
            zone_price_for_rank: dict[str, float] = {}
            operator_id_for_city_zones: dict[str, str | None] = {}

            for zone_key, feats in sorted(zones_map.items(), key=lambda kv: kv[0]):
                # Prefer a feature that has pricing/SMS as the zone prototype
                props = max(
                    (f.get("properties") or {} for f in feats),
                    key=lambda p: (
                        1 if p.get("base_rate") else 0,
                        1 if p.get("payment:sms") else 0,
                        1 if p.get("zone_id") else 0,
                    ),
                )
                z_name = str(
                    props.get("parkingzone_name:sr-Latn-RS")
                    or props.get("parkingzone_name:en-US")
                    or zone_key
                )
                z_slug = slugify(z_name)
                zone_id = ids.unique(f"zone-{city_slug}-{z_slug}")
                zone_ids.append(zone_id)

                try:
                    legacy_zone_id = int(zone_key) if not str(zone_key).startswith("synth-") else None
                except ValueError:
                    legacy_zone_id = None

                # Operator
                op_name = str(props.get("operator") or "").strip()
                operator_id = None
                if op_name:
                    op_key = f"{country_id}:{slugify(op_name)}"
                    if op_key not in operators_by_key:
                        op_id = ids.unique(f"op-{slugify(op_name)}")
                        contact: dict[str, Any] = {}
                        if props.get("contact:email") and str(props["contact:email"]).upper() != "N/A":
                            contact["email"] = str(props["contact:email"])
                        if props.get("contact:website") and str(props["contact:website"]).upper() != "N/A":
                            contact["website"] = str(props["contact:website"])
                        if props.get("contact:phone"):
                            contact["phone"] = str(props["contact:phone"])
                        operators_by_key[op_key] = {
                            "id": op_id,
                            "legacyId": None,
                            "locales": {
                                "sr-Latn": {"name": op_name},
                                "en": {"name": op_name},
                            },
                            "contact": contact or None,
                        }
                    operator_id = operators_by_key[op_key]["id"]
                operator_id_for_city_zones[zone_id] = operator_id

                # Polygons
                polygon_ids: list[str] = []
                for feat in feats:
                    p = feat.get("properties") or {}
                    poly_uuid = p.get("polygon_id")
                    if poly_uuid:
                        poly_id = ids.unique(f"poly-{poly_uuid}")
                    else:
                        poly_id = ids.unique(f"poly-{city_slug}-{z_slug}")
                    polygon_ids.append(poly_id)
                    overrides: dict[str, Any] = {}
                    sub = p.get("parking:zone:subzone") or p.get("podzona")
                    if sub:
                        overrides["locales"] = {
                            "sr-Latn": {"name": f"{z_name} ({sub})"},
                            "en": {"name": f"{z_name} ({sub})"},
                        }
                    polygons_out.append(
                        {
                            "id": poly_id,
                            "zoneId": zone_id,
                            "enabled": True,
                            "ring": ring_from_geometry(feat.get("geometry")),
                            "overrides": overrides,
                            "effectiveFrom": None,
                            "effectiveTo": None,
                        }
                    )

                mode, base_mins, ladder, base_price = build_ladder(
                    props, default_currency
                )
                price_amount = float(base_price["amount"]) if base_price else 0.0
                currency_id = (
                    base_price["currencyId"] if base_price else default_currency
                )
                zone_price_for_rank[zone_id] = price_amount

                max_minutes = parse_duration_minutes(props.get("maxstay"))
                cooldown_mins = parse_duration_minutes(props.get("cooldown_period"))
                rule_ids: list[str] = []
                cooldown_obj = None
                if max_minutes is not None:
                    rule_max_id = ids.unique(f"rule-max-duration-{city_slug}-{z_slug}")
                    rules_out.append(
                        {
                            "id": rule_max_id,
                            "type": "max_duration",
                            "maxDurationMinutes": max_minutes,
                            "notes": "Mapped from GeoJSON maxstay",
                        }
                    )
                    rule_ids.append(rule_max_id)
                    if cooldown_mins is not None or max_minutes is not None:
                        cooldown_obj = {
                            "enabled": True,
                            "resumeNextPaymentWindow": True,
                        }
                        rule_cd_id = ids.unique(f"rule-cooldown-{city_slug}-{z_slug}")
                        rules_out.append(
                            {
                                "id": rule_cd_id,
                                "type": "cooldown_after_max",
                                "enabled": True,
                                "resumeNextPaymentWindow": True,
                                "notes": (
                                    f"Mapped from GeoJSON cooldown_period={props.get('cooldown_period')!r}"
                                    if cooldown_mins is not None
                                    else "Inferred after maxstay"
                                ),
                            }
                        )
                        rule_ids.append(rule_cd_id)

                sms_number = props.get("payment:sms")
                sms_prefix = clean_sms_prefix(props.get("sms_prefix"))
                has_timed = base_price is not None or sms_number is not None

                product_ids: list[str] = []
                payment_method_ids: list[str] = []

                if has_timed:
                    pay_id = ids.unique(f"pay-sms-{city_slug}-{z_slug}")
                    payment_method_ids.append(pay_id)
                    slots = message_slots_from_ladder(mode, base_mins, ladder)
                    payment_methods_out.append(
                        {
                            "id": pay_id,
                            "type": "sms",
                            "enabled": True,
                            "sms": {
                                "number": str(sms_number) if sms_number is not None else None,
                                "prefix": sms_prefix,
                                "messageSlots": slots,
                                "maxDurationMinutes": max_minutes,
                                "cooldownAfterMax": cooldown_obj,
                            },
                            "effectiveFrom": None,
                            "effectiveTo": None,
                        }
                    )

                    prod_id = ids.unique(f"prod-timed-{city_slug}-{z_slug}")
                    product_ids.append(prod_id)
                    products_out.append(
                        {
                            "id": prod_id,
                            "legacyId": legacy_zone_id,
                            "kind": "timed",
                            "zoneIds": [zone_id],
                            "coversZoneIds": [],
                            "locales": zone_locales_from_props(props),
                            "color": props.get("colour"),
                            "price": base_price
                            or {"amount": 0, "currencyId": default_currency},
                            "pricing": {
                                "mode": mode,
                                "baseDurationMinutes": base_mins,
                                "ladder": ladder,
                                "nightRates": [],
                                "seasonalPrices": [],
                            },
                            "validity": {
                                "mode": None,
                                "durationMinutes": (
                                    ladder[0]["durationMinutes"]
                                    if ladder
                                    else (base_mins or 60)
                                ),
                                "buttonColor": None,
                            },
                            "paymentMethodIds": [pay_id],
                            "ruleIds": rule_ids,
                            "eligibility": {"type": "public"},
                            "effectiveFrom": None,
                            "effectiveTo": None,
                        }
                    )
                else:
                    # Hook placeholders for temporary lots without SMS/price
                    pay_id = ids.unique(f"pay-sms-{city_slug}-{z_slug}")
                    payment_method_ids.append(pay_id)
                    payment_methods_out.append(
                        {
                            "id": pay_id,
                            "type": "sms",
                            "enabled": False,
                            "sms": {
                                "number": None,
                                "prefix": "",
                                "messageSlots": [],
                                "maxDurationMinutes": None,
                                "cooldownAfterMax": None,
                            },
                            "effectiveFrom": None,
                            "effectiveTo": None,
                        }
                    )

                # Full-day product (per zone when daily_rate / daily SMS present)
                daily_money = parse_money(props.get("daily_rate"), default_currency)
                daily_sms = props.get("payment:sms:daily")
                if daily_money is not None or daily_sms is not None:
                    d_slug = slugify(f"{z_name}-fullday")
                    d_pay_id = ids.unique(f"pay-sms-fullday-{city_slug}-{d_slug}")
                    d_prod_id = ids.unique(f"prod-fullday-{city_slug}-{d_slug}")
                    d_prefix = clean_sms_prefix(
                        props.get("sms_prefix_daily")
                        if props.get("sms_prefix_daily") is not None
                        else ""
                    )
                    validity_mode = infer_full_day_validity(props)
                    payment_methods_out.append(
                        {
                            "id": d_pay_id,
                            "type": "sms",
                            "enabled": True,
                            "sms": {
                                "number": str(daily_sms) if daily_sms is not None else None,
                                "prefix": d_prefix,
                                "messageSlots": [
                                    {
                                        "index": 1,
                                        "durationMinutes": 1440,
                                        "sendWindow": None,
                                    }
                                ],
                                "maxDurationMinutes": 1440,
                                "cooldownAfterMax": None,
                            },
                            "effectiveFrom": None,
                            "effectiveTo": None,
                        }
                    )
                    products_out.append(
                        {
                            "id": d_prod_id,
                            "legacyId": legacy_zone_id,
                            "kind": "full_day",
                            "zoneIds": [zone_id],
                            "coversZoneIds": [],
                            "locales": {
                                "sr-Latn": {
                                    "name": f"Celodnevna — {z_name}",
                                    "description": str(
                                        props.get("info_note:sr-Latn") or ""
                                    ),
                                },
                                "en": {
                                    "name": f"Full day — {z_name}",
                                    "description": str(
                                        props.get("info_note:en")
                                        or props.get("info_rate:en")
                                        or ""
                                    ),
                                },
                                "ru": {
                                    "name": f"Дневной — {z_name}",
                                    "description": str(props.get("info_note:ru") or ""),
                                },
                            },
                            "color": props.get("colour"),
                            "price": daily_money
                            or {"amount": 0, "currencyId": default_currency},
                            "pricing": {
                                "mode": "fixed",
                                "baseDurationMinutes": 1440,
                                "ladder": [],
                                "nightRates": [],
                                "seasonalPrices": [],
                            },
                            "validity": {
                                "mode": validity_mode,
                                "durationMinutes": 1440,
                                "buttonColor": props.get("colour"),
                            },
                            "paymentMethodIds": [d_pay_id],
                            "ruleIds": [],
                            "eligibility": {"type": "public"},
                            "effectiveFrom": None,
                            "effectiveTo": None,
                        }
                    )
                    product_ids.append(d_prod_id)
                    payment_method_ids.append(d_pay_id)

                # Fine
                fine_money = parse_money(props.get("fine"), default_currency)
                if fine_money is not None:
                    fine_id = ids.unique(f"fine-{city_slug}-{z_slug}")
                    discount = None
                    disc_raw = props.get("fine:discount")
                    if disc_raw:
                        pm = PERCENT_RE.search(str(disc_raw))
                        if pm:
                            discount = {
                                "percent": int(pm.group("p")),
                                "periodDurationMinutes": 8 * 24 * 60
                                if "osam" in str(disc_raw).lower()
                                or "8" in str(disc_raw)
                                else None,
                            }
                    fines_out.append(
                        {
                            "id": fine_id,
                            "operatorId": operator_id,
                            "zoneIds": [zone_id],
                            "amount": fine_money,
                            "discount": discount,
                            "locales": {
                                "sr-Latn": {"name": f"Kazna — {z_name}"},
                                "en": {"name": f"Fine — {z_name}"},
                            },
                        }
                    )

                kinds = []
                for pid in product_ids:
                    for prod in products_out:
                        if prod["id"] == pid:
                            kinds.append(prod["kind"])
                            break
                full_day_only = bool(kinds) and all(k == "full_day" for k in kinds)

                zones_out.append(
                    {
                        "id": zone_id,
                        "legacyId": legacy_zone_id,
                        "cityId": city_id,
                        "enabled": True,
                        "color": props.get("colour") or "#888888",
                        "locales": zone_locales_from_props(props),
                        "polygonIds": polygon_ids,
                        "productIds": product_ids,
                        "paymentMethodIds": payment_method_ids,
                        "paymentWindows": parse_fee_conditional(
                            props.get("fee:conditional")
                        ),
                        "workingDayOverrides": [],
                        "eligibility": {"type": "public"},
                        "fullDayOnly": full_day_only,
                        "seasonalWindows": [],
                        "operatorId": operator_id,
                        "effectiveFrom": None,
                        "effectiveTo": None,
                    }
                )

            # Coverage policy (unchanged design)
            ranked = sorted(
                zone_price_for_rank.items(), key=lambda kv: kv[1], reverse=True
            )
            coverage_zone_entries = []
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
                policy_id = ids.unique(f"coverage-{city_slug}")
                coverage_policies.append(
                    {
                        "id": policy_id,
                        "cityId": city_id,
                        "onOverlap": "offer_highest_rank",
                        "zones": coverage_zone_entries,
                    }
                )

            cities_out.append(
                {
                    "id": city_id,
                    "legacyId": legacy_city_id,
                    "countryId": country_id,
                    "timezone": tz,
                    "shortName": sample.get("city_short_name"),
                    "center": center,
                    "locales": city_locales_from_props(sample),
                    "zoneIds": zone_ids,
                    "coveragePolicyId": policy_id,
                    "coveragePolygon": None,
                    "fullDayButtonColor": None,
                    "effectiveFrom": None,
                    "effectiveTo": None,
                }
            )

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

    return {
        "dataVersion": data_version,
        "minAppVersion": min_app_version,
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": {
            "url": None,
            "legacyVersion": None,
            "notes": (
                "GeoJSON import: "
                + "; ".join(source_notes)
                + ". SMS sendWindow / city cases / coversZoneIds need manual fill."
            ),
        },
        "locales": LOCALE_CATALOG,
        "currencies": CURRENCY_SEED,
        "countries": countries,
        "operators": list(operators_by_key.values()),
        "cities": cities_out,
        "zones": zones_out,
        "polygons": polygons_out,
        "products": products_out,
        "paymentMethods": payment_methods_out,
        "rules": rules_out,
        "coveragePolicies": coverage_policies,
        "residentPermits": [],
        "fines": fines_out,
    }


def make_sample(config: dict[str, Any], city_ids: list[str]) -> dict[str, Any]:
    """Shrink config to selected cities; truncate polygon rings for readability."""
    city_set = set(city_ids)
    cities = [c for c in config["cities"] if c["id"] in city_set]
    zone_ids = {z for c in cities for z in (c.get("zoneIds") or [])}
    zones = [z for z in config["zones"] if z["id"] in zone_ids]
    poly_ids = {p for z in zones for p in (z.get("polygonIds") or [])}
    polygons = []
    for p in config["polygons"]:
        if p["id"] not in poly_ids:
            continue
        ring = p.get("ring") or []
        clipped = dict(p)
        if len(ring) > 8:
            clipped["ring"] = ring[:3] + ring[-1:]
            clipped["_ringTruncated"] = True
            clipped["_ringPointCount"] = len(ring)
        polygons.append(clipped)
    product_ids = {pid for z in zones for pid in (z.get("productIds") or [])}
    products = [p for p in config["products"] if p["id"] in product_ids]
    pay_ids = {pid for z in zones for pid in (z.get("paymentMethodIds") or [])}
    for p in products:
        pay_ids.update(p.get("paymentMethodIds") or [])
    payment_methods = [
        m
        for m in config["paymentMethods"]
        if m["id"] in pay_ids or m["id"] == "pay-webview-card-example"
    ]
    rule_ids = {rid for p in products for rid in (p.get("ruleIds") or [])}
    rules = [r for r in config["rules"] if r["id"] in rule_ids]
    coverage = [
        c for c in config["coveragePolicies"] if c.get("cityId") in city_set
    ]
    op_ids = {z.get("operatorId") for z in zones if z.get("operatorId")}
    operators = [o for o in config["operators"] if o["id"] in op_ids]
    fines = [
        f
        for f in config["fines"]
        if any(zid in zone_ids for zid in (f.get("zoneIds") or []))
    ]
    country_ids = {c["countryId"] for c in cities}
    return {
        "dataVersion": config["dataVersion"],
        "minAppVersion": config["minAppVersion"],
        "generatedAt": config.get("generatedAt"),
        "source": {
            **(config.get("source") or {}),
            "notes": (
                (config.get("source") or {}).get("notes", "")
                + f" Sample cities only: {', '.join(city_ids)}. Polygon rings truncated."
            ).strip(),
        },
        "locales": config["locales"],
        "currencies": config["currencies"],
        "countries": [c for c in config["countries"] if c["id"] in country_ids],
        "operators": operators,
        "cities": cities,
        "zones": zones,
        "polygons": polygons,
        "products": products,
        "paymentMethods": payment_methods,
        "rules": rules,
        "coveragePolicies": coverage,
        "residentPermits": [],
        "fines": fines,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert parking GeoJSON files to parking-config JSON."
    )
    parser.add_argument(
        "--rs",
        type=Path,
        help="Path to Serbia ParkingZonesWithUUID.geojson",
    )
    parser.add_argument(
        "--me",
        type=Path,
        help="Path to Montenegro parkingZonesMontenegroUUID.geojson",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        required=True,
        help="Output parking-config JSON path (keep private)",
    )
    parser.add_argument(
        "--sample-output",
        type=Path,
        help="Optional truncated sample JSON (1–2 cities)",
    )
    parser.add_argument(
        "--sample-cities",
        nargs="+",
        default=["city-beograd", "city-podgorica"],
        help="City ids to include in --sample-output",
    )
    parser.add_argument("--data-version", default="1.0.0-geojson")
    parser.add_argument("--min-app-version", default="5.0.0")
    args = parser.parse_args()

    inputs: list[tuple[Path, str]] = []
    if args.rs:
        inputs.append((args.rs, "rs"))
    if args.me:
        inputs.append((args.me, "me"))
    if not inputs:
        parser.error("Provide at least one of --rs / --me")

    for path, _ in inputs:
        if not path.is_file():
            raise SystemExit(f"Input not found: {path}")

    config = transform_geojson_files(
        inputs,
        data_version=args.data_version,
        min_app_version=args.min_app_version,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(
        "Wrote"
        f" cities={len(config['cities'])}"
        f" zones={len(config['zones'])}"
        f" polygons={len(config['polygons'])}"
        f" products={len(config['products'])}"
        f" paymentMethods={len(config['paymentMethods'])}"
        f" → {args.output}"
    )

    if args.sample_output:
        # Resolve sample city ids that actually exist
        available = {c["id"] for c in config["cities"]}
        chosen = [c for c in args.sample_cities if c in available]
        if not chosen:
            # fallback: first RS + first ME if present
            by_country: dict[str, list[str]] = defaultdict(list)
            for c in config["cities"]:
                by_country[c["countryId"]].append(c["id"])
            chosen = []
            if by_country.get("rs"):
                chosen.append(by_country["rs"][0])
            if by_country.get("me"):
                chosen.append(by_country["me"][0])
            if not chosen and config["cities"]:
                chosen = [config["cities"][0]["id"]]
        sample = make_sample(config, chosen)
        args.sample_output.parent.mkdir(parents=True, exist_ok=True)
        with args.sample_output.open("w", encoding="utf-8") as f:
            json.dump(sample, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"Sample cities={chosen} → {args.sample_output}")


if __name__ == "__main__":
    main()
