"""Evidence-based matching of Windows Update offers to installed devices.

Only exact hardware IDs count as matches. Version comparisons are informational;
Windows Update applicability is independent of numeric version ordering.
"""
from __future__ import annotations

import re


def compare_versions(installed: str | None, offered: str | None) -> str:
    """Compare strictly numeric dotted versions; otherwise unknown."""
    pattern = re.compile(r"^\d+(?:\.\d+){1,7}$")
    if not installed or not offered or not pattern.fullmatch(str(installed)) or not pattern.fullmatch(str(offered)):
        return "unknown"
    a = tuple(int(x) for x in str(installed).split("."))
    b = tuple(int(x) for x in str(offered).split("."))
    width = max(len(a), len(b))
    a += (0,) * (width - len(a))
    b += (0,) * (width - len(b))
    return "newer" if b > a else "same" if b == a else "older"


def match_offers(devices: list[dict], offers: list[dict]) -> dict:
    index: dict[str, list[dict]] = {}
    for device in devices:
        for raw in device.get("hardware_ids") or []:
            key = str(raw).strip().upper()
            if key:
                index.setdefault(key, []).append(device)
    matched, unmatched = [], []
    for offer in offers:
        key = str(offer.get("driver_hardware_id") or "").strip().upper()
        candidates = index.get(key, []) if key else []
        if len(candidates) != 1:
            unmatched.append({
                "offer": offer,
                "reason": "missing_hardware_id" if not key else
                          "ambiguous_hardware_id" if len(candidates) > 1 else "no_exact_hardware_id_match",
            })
            continue
        device = candidates[0]
        matched.append({
            "device": device,
            "offer": offer,
            "match": "exact_hardware_id",
            "version_comparison": compare_versions(device.get("driver_version"), offer.get("driver_version")),
            "recommendation": "manual_review",
        })
    return {
        "matched": matched,
        "unmatched": unmatched,
        "note": "Exact ID matches only. No automatic installation. Compare OS, architecture, OEM policy, signatures and release notes before approval.",
    }
