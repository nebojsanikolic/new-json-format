#!/usr/bin/env python3
"""Split a monolith parking-config JSON into manifest + shared + per-city files.

Production delivery layout:

  <out>/
    manifest.json
    shared.json
    cities/<cityId>.json

The monolith remains useful for tools and transforms; this script is the
publish step. See docs/delivery-manifest.md for forceUpdate semantics.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SHARED_KEYS = ("locales", "currencies", "countries", "operators")
CITY_ARRAY_KEYS = (
    "cities",
    "zones",
    "polygons",
    "products",
    "paymentMethods",
    "rules",
    "coveragePolicies",
    "residentPermits",
    "fines",
)

DEFAULT_CLIENT = {
    "supportedLocales": ["sr-Latn", "sr-Cyrl", "en", "ru"],
    "localeFallback": ["sr-Latn", "en", "sr-Cyrl", "ru"],
}

LOCALE_IDS = ("sr-Latn", "sr-Cyrl", "en", "ru")


def _resolve_client(config: dict[str, Any]) -> dict[str, Any]:
    raw = config.get("client") or {}
    supported = raw.get("supportedLocales") or DEFAULT_CLIENT["supportedLocales"]
    fallback = raw.get("localeFallback") or DEFAULT_CLIENT["localeFallback"]
    return {
        "supportedLocales": list(supported),
        "localeFallback": list(fallback),
    }


def _complete_locales_map(partial: dict[str, Any] | None) -> dict[str, Any]:
    src = dict(partial or {})
    fallback: dict[str, Any] = {}
    for lid in ("sr-Latn", "en", "sr-Cyrl", "ru"):
        if src.get(lid):
            fallback = dict(src[lid])
            break
    if not fallback:
        for entry in src.values():
            if entry:
                fallback = dict(entry)
                break
    return {lid: dict(src.get(lid) or fallback) for lid in LOCALE_IDS}


def _split_holidays(config: dict[str, Any]) -> tuple[list[dict], list[dict]]:
    """Country-scoped (no cityId) → shared; city-scoped → city slices."""
    all_holidays = list(config.get("holidays") or [])
    country = [h for h in all_holidays if not h.get("cityId")]
    city = [h for h in all_holidays if h.get("cityId")]
    return country, city


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _version_stamp(prefix: str | None = None) -> str:
    """Date-based revision: YYYY.MM.DD.N (N defaults to 1)."""
    day = datetime.now(timezone.utc).strftime("%Y.%m.%d")
    stamp = f"{day}.1"
    return f"{prefix}-{stamp}" if prefix else stamp


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_checksum(data: bytes) -> str:
    """Manifest integrity field: sha256:<hex> of exact UTF-8 file bytes."""
    return f"sha256:{_sha256_bytes(data)}"


def _dump_json(path: Path, obj: Any, *, pretty: bool) -> bytes:
    path.parent.mkdir(parents=True, exist_ok=True)
    if pretty:
        text = json.dumps(obj, ensure_ascii=False, indent=2) + "\n"
    else:
        text = json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n"
    raw = text.encode("utf-8")
    path.write_bytes(raw)
    return raw


def _index_by_id(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in items if "id" in item}


def _zone_ids_for_city(city: dict[str, Any], zones_by_city: dict[str, list[dict]]) -> set[str]:
    from_list = set(city.get("zoneIds") or [])
    from_zones = {z["id"] for z in zones_by_city.get(city["id"], [])}
    return from_list | from_zones


def split_config(
    config: dict[str, Any],
    *,
    schema_version: str = "1.0.0",
    main_version: str | None = None,
    shared_version: str | None = None,
    city_version: str | None = None,
    force_update_main: bool = False,
    force_update_shared: bool = False,
    force_update_cities: set[str] | None = None,
    force_update_all_cities: bool = False,
    include_checksum: bool = True,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, dict[str, Any]]]:
    """Return (manifest, shared, cities_by_id)."""
    force_update_cities = force_update_cities or set()
    main_version = main_version or config.get("dataVersion") or _version_stamp("main")
    shared_version = shared_version or _version_stamp("shared")
    default_city_version = city_version or _version_stamp()

    shared: dict[str, Any] = {
        "schemaVersion": schema_version,
        "version": shared_version,
        "generatedAt": config.get("generatedAt") or _utc_now(),
        "client": _resolve_client(config),
    }
    for key in SHARED_KEYS:
        shared[key] = list(config.get(key) or [])

    country_holidays, city_holidays = _split_holidays(config)
    shared["holidays"] = country_holidays

    zones = list(config.get("zones") or [])
    zones_by_city: dict[str, list[dict[str, Any]]] = {}
    for zone in zones:
        zones_by_city.setdefault(zone.get("cityId") or "", []).append(zone)

    polygons = list(config.get("polygons") or [])
    products = list(config.get("products") or [])
    payment_methods = list(config.get("paymentMethods") or [])
    payment_by_id = _index_by_id(payment_methods)
    rules = list(config.get("rules") or [])
    rules_by_id = _index_by_id(rules)
    coverage_policies = list(config.get("coveragePolicies") or [])
    resident_permits = list(config.get("residentPermits") or [])
    fines = list(config.get("fines") or [])

    cities_out: dict[str, dict[str, Any]] = {}
    manifest_cities: list[dict[str, Any]] = []

    for city in config.get("cities") or []:
        city_id = city["id"]
        country_id = city.get("countryId")
        zone_ids = _zone_ids_for_city(city, zones_by_city)
        city_zones = [z for z in zones if z.get("id") in zone_ids or z.get("cityId") == city_id]
        zone_ids = {z["id"] for z in city_zones}

        city_polygons = [p for p in polygons if p.get("zoneId") in zone_ids]
        city_products = [
            p for p in products if zone_ids.intersection(p.get("zoneIds") or [])
        ]
        product_ids = {p["id"] for p in city_products}

        payment_ids: set[str] = set()
        for zone in city_zones:
            payment_ids.update(zone.get("paymentMethodIds") or [])
        for product in city_products:
            payment_ids.update(product.get("paymentMethodIds") or [])
        city_payments = [
            payment_by_id[pid] for pid in sorted(payment_ids) if pid in payment_by_id
        ]

        rule_ids: set[str] = set()
        for product in city_products:
            rule_ids.update(product.get("ruleIds") or [])
        city_rules = [rules_by_id[rid] for rid in sorted(rule_ids) if rid in rules_by_id]

        city_coverage = [c for c in coverage_policies if c.get("cityId") == city_id]
        city_fines = [f for f in fines if zone_ids.intersection(f.get("zoneIds") or [])]
        city_residents = [
            r
            for r in resident_permits
            if r.get("cityId") == city_id
            or zone_ids.intersection(r.get("zoneIds") or [])
        ]

        city_ver = default_city_version
        force = force_update_all_cities or city_id in force_update_cities

        holidays_for_city = [
            h for h in city_holidays if h.get("cityId") == city_id
        ]

        slice_obj: dict[str, Any] = {
            "cityId": city_id,
            "countryId": country_id,
            "version": city_ver,
            "schemaVersion": schema_version,
            "generatedAt": config.get("generatedAt") or _utc_now(),
            "city": city,
            "zones": city_zones,
            "polygons": city_polygons,
            "products": city_products,
            "paymentMethods": city_payments,
            "rules": city_rules,
            "coveragePolicies": city_coverage,
            "residentPermits": city_residents,
            "fines": city_fines,
            "holidays": holidays_for_city,
        }
        cities_out[city_id] = slice_obj

        entry: dict[str, Any] = {
            "cityId": city_id,
            "countryId": country_id,
            "version": city_ver,
            "forceUpdate": force,
            "url": f"cities/{city_id}.json",
        }
        manifest_cities.append(entry)

    manifest_cities.sort(key=lambda c: c["cityId"])

    # v1: full country objects stay in shared.json; manifest lists an index.
    manifest_countries: list[dict[str, Any]] = []
    for country in config.get("countries") or []:
        cid = country.get("id")
        if not cid:
            continue
        entry: dict[str, Any] = {
            "countryId": cid,
            "timezone": country.get("timezone") or "",
            "locales": _complete_locales_map(country.get("locales")),
            "version": shared_version,
            "forceUpdate": force_update_shared,
            "url": "shared.json",
        }
        if force_update_shared:
            entry["updatedAt"] = _utc_now()
        manifest_countries.append(entry)
    manifest_countries.sort(key=lambda c: c["countryId"])

    manifest: dict[str, Any] = {
        "schemaVersion": schema_version,
        "minAppVersion": config.get("minAppVersion") or "5.0.0",
        "mainVersion": main_version,
        "forceUpdate": force_update_main,
        "generatedAt": config.get("generatedAt") or _utc_now(),
        "shared": {
            "version": shared_version,
            "forceUpdate": force_update_shared,
            "url": "shared.json",
        },
        "countries": manifest_countries,
        "cities": manifest_cities,
    }
    if config.get("source"):
        manifest["source"] = config["source"]

    return manifest, shared, cities_out


def write_delivery(
    out_dir: Path,
    manifest: dict[str, Any],
    shared: dict[str, Any],
    cities: dict[str, dict[str, Any]],
    *,
    pretty: bool = True,
    include_checksum: bool = True,
) -> dict[str, Any]:
    """Write files; fill checksum + contentHash on shared and city entries."""
    out_dir.mkdir(parents=True, exist_ok=True)
    cities_dir = out_dir / "cities"
    cities_dir.mkdir(parents=True, exist_ok=True)

    shared_raw = _dump_json(out_dir / "shared.json", shared, pretty=pretty)
    if include_checksum:
        digest = _sha256_checksum(shared_raw)
        manifest["shared"]["checksum"] = digest
        manifest["shared"]["contentHash"] = digest
        for entry in manifest.get("countries") or []:
            if entry.get("url") == "shared.json":
                entry["checksum"] = digest
                entry["contentHash"] = digest

    checksum_by_city: dict[str, str] = {}
    for city_id, slice_obj in cities.items():
        raw = _dump_json(cities_dir / f"{city_id}.json", slice_obj, pretty=pretty)
        if include_checksum:
            checksum_by_city[city_id] = _sha256_checksum(raw)

    if include_checksum:
        for entry in manifest["cities"]:
            cid = entry["cityId"]
            if cid in checksum_by_city:
                digest = checksum_by_city[cid]
                entry["checksum"] = digest
                entry["contentHash"] = digest

    _dump_json(out_dir / "manifest.json", manifest, pretty=pretty)

    return {
        "outDir": str(out_dir),
        "cityCount": len(cities),
        "sharedOperators": len(shared.get("operators") or []),
        "forceUpdateCities": sum(1 for c in manifest["cities"] if c.get("forceUpdate")),
    }


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise SystemExit(f"Expected object at root of {path}")
    return data


def parse_force_cities(raw: str | None) -> set[str]:
    if not raw:
        return set()
    parts = re.split(r"[,;\s]+", raw.strip())
    return {p for p in parts if p}


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Split monolith parking-config into manifest + shared + cities."
    )
    p.add_argument(
        "-i",
        "--input",
        type=Path,
        required=True,
        help="Monolith parking-config JSON path",
    )
    p.add_argument(
        "-o",
        "--output",
        type=Path,
        required=True,
        help="Output directory (manifest.json, shared.json, cities/)",
    )
    p.add_argument("--schema-version", default="1.0.0")
    p.add_argument("--main-version", default=None, help="Override manifest mainVersion")
    p.add_argument("--shared-version", default=None)
    p.add_argument(
        "--city-version",
        default=None,
        help="Version stamped on every city file (default: YYYY.MM.DD.1)",
    )
    p.add_argument(
        "--force-update-main",
        action="store_true",
        help="Set forceUpdate on the manifest root",
    )
    p.add_argument(
        "--force-update-shared",
        action="store_true",
        help="Set shared.forceUpdate",
    )
    p.add_argument(
        "--force-update-cities",
        default=None,
        help="Comma-separated cityIds that must forceUpdate (e.g. city-beograd)",
    )
    p.add_argument(
        "--force-update-all-cities",
        action="store_true",
        help="Set forceUpdate on every city (e.g. global price/SMS cutover)",
    )
    p.add_argument(
        "--no-checksum",
        action="store_true",
        help="Omit SHA-256 checksum fields on city manifest entries",
    )
    p.add_argument(
        "--compact",
        action="store_true",
        help="Write minified JSON (default: pretty)",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    config = load_json(args.input)
    # Quick sanity: monolith should have cities
    if not config.get("cities"):
        raise SystemExit("Input has no cities[] — not a parking-config monolith?")

    unused = set(CITY_ARRAY_KEYS)  # documented for readers / future checks
    _ = unused

    manifest, shared, cities = split_config(
        config,
        schema_version=args.schema_version,
        main_version=args.main_version,
        shared_version=args.shared_version,
        city_version=args.city_version,
        force_update_main=args.force_update_main,
        force_update_shared=args.force_update_shared,
        force_update_cities=parse_force_cities(args.force_update_cities),
        force_update_all_cities=args.force_update_all_cities,
        include_checksum=not args.no_checksum,
    )
    stats = write_delivery(
        args.output,
        manifest,
        shared,
        cities,
        pretty=not args.compact,
        include_checksum=not args.no_checksum,
    )
    print(
        f"Wrote {stats['cityCount']} cities → {stats['outDir']} "
        f"(forceUpdate cities={stats['forceUpdateCities']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
