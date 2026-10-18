#!/usr/bin/env python3
"""Migrate {latitude,longitude} points → [lat, lon] arrays; fix truncated rings."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def round6(v: Any) -> float:
    return round(float(v), 6)


def convert_point(p: Any) -> list[float] | None:
    if isinstance(p, (list, tuple)) and len(p) >= 2:
        return [round6(p[0]), round6(p[1])]
    if isinstance(p, dict) and "latitude" in p and "longitude" in p:
        if p.get("_truncated"):
            return None  # drop sentinel
        return [round6(p["latitude"]), round6(p["longitude"])]
    return None


def convert_ring(ring: Any) -> tuple[list[list[float]], bool]:
    """Return (new_ring, saw_truncated_sentinel)."""
    if not isinstance(ring, list):
        return [], False
    out: list[list[float]] = []
    truncated = False
    for p in ring:
        if isinstance(p, dict) and p.get("_truncated"):
            truncated = True
            continue
        pt = convert_point(p)
        if pt is not None:
            out.append(pt)
    return out, truncated


def migrate(obj: Any) -> Any:
    if isinstance(obj, list):
        return [migrate(x) for x in obj]
    if not isinstance(obj, dict):
        return obj

    out: dict[str, Any] = {}
    for k, v in obj.items():
        if k == "ring" and isinstance(v, list):
            ring, sentinel = convert_ring(v)
            out["ring"] = ring
            if sentinel or obj.get("ringTruncated") or obj.get("_ringTruncated"):
                out["ringTruncated"] = True
            continue
        if k in ("_ringTruncated", "_ringPointCount", "_truncated"):
            continue
        if k in ("center",) or k.endswith("Polygon") or k == "coveragePolygon":
            if isinstance(v, dict) and "latitude" in v:
                out[k] = convert_point(v)
                continue
            if isinstance(v, list) and v and isinstance(v[0], dict):
                ring, _ = convert_ring(v)
                out[k] = ring
                continue
        out[k] = migrate(v)

    # polygons may carry ringTruncated from legacy keys already handled
    if "ring" in out and obj.get("_ringTruncated") and "ringTruncated" not in out:
        out["ringTruncated"] = True
    return out


def migrate_file(path: Path) -> tuple[int, int, float]:
    raw = path.read_bytes()
    before = len(raw)
    data = json.loads(raw.decode("utf-8"))
    migrated = migrate(data)
    text = json.dumps(migrated, ensure_ascii=False, indent=2) + "\n"
    path.write_text(text, encoding="utf-8")
    after = len(text.encode("utf-8"))
    return before, after, (1 - after / before) * 100 if before else 0.0


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    paths = [
        root / "data" / "parking-config.generated.json",
        root / "examples" / "belgrade-snippet.json",
        root / "examples" / "delivery" / "cities" / "city-beograd.json",
        root / "examples" / "delivery" / "shared.json",
    ]
    # optional store copies handled separately
    for p in paths:
        if not p.exists():
            print(f"skip missing {p}")
            continue
        before, after, pct = migrate_file(p)
        print(f"{p.relative_to(root)}: {before:,} → {after:,} bytes ({pct:.1f}% smaller)")


if __name__ == "__main__":
    main()
