"""Deterministic, allowlisted driver research tools for the AI worker.

AI receives tool observations; it cannot choose arbitrary URLs or invoke downloads.
"""
from __future__ import annotations

from .dell import dell_driver_packs
from .downloads import validate_source, DownloadError


def collect_oem_evidence(system: dict) -> dict:
    manufacturer = str(system.get("manufacturer") or "")
    model = str(system.get("model") or "")
    if "dell" in manufacturer.casefold():
        try:
            result = dell_driver_packs(manufacturer, model)
            packages = []
            for pack in result["packages"][:50]:
                try:
                    validate_source(pack["url"], "dell")
                except DownloadError:
                    continue
                packages.append({
                    "vendor": "dell", "model": model, "url": pack["url"],
                    "status": "model_match_only",
                    "release_id": pack.get("release_id"),
                    "sha256": None, "device_match": False,
                    "os_match": False, "signature_verified": False,
                })
            return {"provider": "dell", "packages": packages, "catalogue_checked": True,
                    "note": "Deployment packs only. Neither OS nor individual device applicability established."}
        except Exception as exc:
            return {"provider": "dell", "catalogue_checked": False,
                    "error": type(exc).__name__, "packages": []}
    return {"provider": manufacturer, "catalogue_checked": False, "packages": [],
            "note": "No supported direct live catalogue adapter for this OEM yet."}


def download_candidate(candidate: dict, output_dir: str, *, approved: bool = False) -> dict:
    """No AI-driven downloads. Require separate explicit user approval and verified hash."""
    if not approved:
        raise PermissionError("User approval required; AI cannot authorize downloads")
    if candidate.get("status") != "exact_hardware_os_match":
        raise ValueError("Exact hardware and OS compatibility not established")
    if not candidate.get("sha256"):
        raise ValueError("Trusted catalogue SHA-256 required")
    from .downloads import download_package
    return download_package(candidate["url"], candidate["vendor"], output_dir,
                            sha256=candidate["sha256"])
