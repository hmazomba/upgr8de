"""Pin catalogue bytes and derive download candidates from exact hardware/OS matches.

Trust is established by a SHA-256 supplied independently by the operator.
An arbitrary catalogue cannot self-certify its own authenticity.
"""
from __future__ import annotations

import hashlib
import hmac
import re
from pathlib import Path

from .catalogue import load_catalogue, candidates
from .downloads import validate_source
from .matching import compare_versions

HEX64 = re.compile(r"^[a-fA-F0-9]{64}$")


class VerificationError(ValueError):
    pass


def verified_catalogue_candidates(path: str, expected_digest: str, devices: list[dict],
                                  system: dict) -> list[dict]:
    if not HEX64.fullmatch(expected_digest):
        raise VerificationError("Expected independently obtained catalogue SHA-256")
    source = Path(path)
    if source.stat().st_size > 5_000_000:
        raise VerificationError("Catalogue too large")
    actual = hashlib.sha256(source.read_bytes()).hexdigest()
    if not hmac.compare_digest(actual, expected_digest.lower()):
        raise VerificationError("Catalogue digest mismatch")
    packages = load_catalogue(path)
    manufacturer = str(system.get("manufacturer") or "").casefold()
    model = str(system.get("model") or "")
    os_name = str(system.get("os_caption") or "")
    arch = str(system.get("architecture") or "")
    matches = candidates(devices, packages, model=model, os_name=os_name, architecture=arch)
    output = []
    seen = set()
    for item in matches:
        pkg = item["package"]
        vendor = str(pkg["vendor"]).casefold()
        if not any(token in manufacturer for token in {
            "hp": ("hp", "hewlett"), "dell": ("dell",),
            "lenovo": ("lenovo",), "asus": ("asus",)
        }.get(vendor, ())):
            continue
        if item["comparison"] != "newer":
            continue
        try:
            validate_source(pkg["url"], vendor)
        except (ValueError, KeyError):
            continue
        key = (pkg["url"], pkg["hardware_id"].upper())
        if key in seen:
            continue
        seen.add(key)
        output.append({
            "vendor": vendor, "url": pkg["url"], "sha256": pkg["sha256"].lower(),
            "device": item["device"], "hardware_id": pkg["hardware_id"],
            "model": model, "os": os_name, "architecture": arch,
            "version": pkg["version"], "comparison": item["comparison"],
            "status": "exact_hardware_os_match",
            "source_verified": True, "hardware_id_verified": True, "os_verified": True,
            "provenance": "operator_pinned_catalogue_sha256",
            "note": "Exact metadata match in operator-pinned catalogue; downloaded bytes still require hash verification. Signature and publisher authorization not verified.",
        })
    return output
