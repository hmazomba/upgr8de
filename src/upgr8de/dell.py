"""Direct Dell driver-pack catalogue reader. No Dell software dependency.

Dell's deployment driver packs are model/OS bundles, not per-device updates.
"""
from __future__ import annotations

import os
import platform
import subprocess
import tempfile
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

from .windows import DiscoveryError

CATALOG_URL = "https://downloads.dell.com/catalog/DriverPackCatalog.cab"
MAX_CAB = 30 * 1024 * 1024


def _download_catalogue(destination: Path) -> None:
    req = urllib.request.Request(CATALOG_URL, headers={"User-Agent": "upgr8de/0.1"})
    with urllib.request.urlopen(req, timeout=40) as response:
        if response.geturl() != CATALOG_URL:
            raise DiscoveryError("Dell catalogue redirected unexpectedly")
        length = response.headers.get("Content-Length")
        if length and int(length) > MAX_CAB:
            raise DiscoveryError("Dell catalogue exceeds size limit")
        with destination.open("wb") as out:
            size = 0
            while chunk := response.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_CAB:
                    raise DiscoveryError("Dell catalogue exceeds size limit")
                out.write(chunk)


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_catalogue(xml_bytes: bytes, model: str) -> list[dict]:
    if len(xml_bytes) > 60 * 1024 * 1024 or b"<!DOCTYPE" in xml_bytes.upper() or b"<!ENTITY" in xml_bytes.upper():
        raise DiscoveryError("Unsupported catalogue XML")
    root = ET.fromstring(xml_bytes)
    matches = []
    for package in root.iter():
        if _local(package.tag) != "DriverPackage":
            continue
        models = []
        for element in package.iter():
            if _local(element.tag) == "Model":
                models.extend(str(v) for v in element.attrib.values())
        if not any(model.casefold() == item.casefold() for item in models):
            continue
        path = package.attrib.get("path") or package.attrib.get("Path") or ""
        if not path or path.startswith(("/", "\\")) or ".." in path.replace("\\", "/").split("/"):
            continue
        url = "https://downloads.dell.com/" + path.replace("\\", "/")
        matches.append({
            "model": model,
            "package_path": path,
            "url": url,
            "package_type": package.attrib.get("type") or package.attrib.get("Type"),
            "release_id": package.attrib.get("releaseID") or package.attrib.get("ReleaseID"),
            "status": "model_match_only",
        })
    return matches


def dell_driver_packs(manufacturer: str, model: str) -> dict:
    if platform.system() != "Windows":
        raise DiscoveryError("Dell catalogue discovery requires Windows.")
    if "dell" not in manufacturer.casefold():
        raise DiscoveryError("Dell catalogue discovery requires a Dell computer.")
    if not model.strip():
        raise DiscoveryError("Dell model unavailable")
    with tempfile.TemporaryDirectory(prefix="upgr8de-dell-") as directory:
        root = Path(directory)
        cab = root / "DriverPackCatalog.cab"
        _download_catalogue(cab)
        # Windows built-in expand.exe extracts only named XML; no package execution.
        try:
            result = subprocess.run(
                ["expand.exe", str(cab), "-F:DriverPackCatalog.xml", str(root)],
                capture_output=True, text=True, timeout=40, check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise DiscoveryError(f"Dell catalogue extraction failed: {exc}") from exc
        if result.returncode:
            raise DiscoveryError(result.stderr.strip() or "Dell catalogue extraction failed")
        xml = root / "DriverPackCatalog.xml"
        if not xml.is_file():
            raise DiscoveryError("Dell catalogue XML missing")
        packs = parse_catalogue(xml.read_bytes(), model)
    return {
        "provider": "Dell Command Deploy Driver Pack Catalog",
        "catalogue_url": CATALOG_URL,
        "packages": packs,
        "note": "Model matches only; deployment packs are not verified per-device updates. OS applicability and package authenticity require review. Nothing installed.",
    }
