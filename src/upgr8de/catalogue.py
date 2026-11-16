"""Validate a locally supplied OEM driver catalogue, without trusting or fetching it.

Catalogue entries are untrusted metadata. No installation or download happens.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from .matching import compare_versions

HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")
VERSION = re.compile(r"^\d+(?:\.\d+){1,7}$")


class CatalogueError(ValueError):
    pass


def load_catalogue(path: str) -> list[dict]:
    p = Path(path)
    if p.stat().st_size > 5_000_000:
        raise CatalogueError("Catalogue exceeds 5 MB limit")
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1 or not isinstance(data.get("packages"), list):
        raise CatalogueError("Expected schema_version=1 and packages array")
    if len(data["packages"]) > 10000:
        raise CatalogueError("Too many catalogue packages")
    validated = []
    for index, entry in enumerate(data["packages"]):
        if not isinstance(entry, dict):
            raise CatalogueError(f"Package {index}: invalid object")
        required = ("vendor", "model", "hardware_id", "version", "os", "architecture", "url", "sha256")
        if any(not isinstance(entry.get(k), str) or not entry[k].strip() for k in required):
            raise CatalogueError(f"Package {index}: missing required string")
        url = urlsplit(entry["url"])
        if url.scheme != "https" or not url.hostname or url.username or url.password:
            raise CatalogueError(f"Package {index}: HTTPS URL required")
        if not HEX64.fullmatch(entry["sha256"]) or not VERSION.fullmatch(entry["version"]):
            raise CatalogueError(f"Package {index}: invalid SHA256 or version")
        validated.append(entry)
    return validated


def candidates(devices: list[dict], packages: list[dict], *, model: str, os_name: str, architecture: str) -> list[dict]:
    """Require exact hardware ID, model, OS and architecture before comparison."""
    results = []
    for device in devices:
        ids = {str(x).strip().upper() for x in device.get("hardware_ids") or []}
        for pkg in packages:
            if (pkg["hardware_id"].strip().upper() not in ids
                or pkg["model"].casefold() != model.casefold()
                or pkg["os"].casefold() != os_name.casefold()
                or pkg["architecture"].casefold() != architecture.casefold()):
                continue
            results.append({
                "device": device.get("name"),
                "installed_version": device.get("driver_version"),
                "package": pkg,
                "comparison": compare_versions(device.get("driver_version"), pkg["version"]),
                "status": "unverified_catalogue_entry",
                "action": "manual_review_only",
            })
    return results


def verify_file(path: str, expected_sha256: str) -> dict:
    """Verify bytes of a file already present on disk. No execution or signature check."""
    if not HEX64.fullmatch(expected_sha256):
        raise CatalogueError("Expected 64-character SHA-256 hex digest")
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    actual = digest.hexdigest()
    return {"file": str(path), "expected_sha256": expected_sha256.lower(),
            "actual_sha256": actual, "matches": actual == expected_sha256.lower(),
            "signature_verified": False}
