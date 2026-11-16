"""Read-only HP CMSL live SoftPaq catalogue adapter.

Requires separately installed, trusted HP.ClientManagement PowerShell module.
Does not install modules, download SoftPaq packages, or run installers.
"""
from __future__ import annotations

import json
import platform
import subprocess

from .windows import DiscoveryError, _as_list

SCRIPT = r'''
$ErrorActionPreference = 'Stop'
$module = Get-Module -ListAvailable -Name HPCMSL | Select-Object -First 1
if (-not $module) { throw 'HP CMSL is not installed. Install it separately from HP official site.' }
Import-Module HPCMSL -ErrorAction Stop
if (-not (Get-Command Get-SoftpaqList -ErrorAction SilentlyContinue)) {
    throw 'HP CMSL Get-SoftpaqList unavailable'
}
# Get-SoftpaqList queries HP reference metadata for current platform.
# Explicitly omit -Download and -DownloadMetadata switches.
$items = @(Get-SoftpaqList -ErrorAction Stop)
$rows = @()
foreach ($item in $items) {
    $rows += [pscustomobject]@{
        id = [string]$item.Id
        name = [string]$item.Name
        version = [string]$item.Version
        category = [string]$item.Category
        release_date = [string]$item.ReleaseDate
        url = [string]$item.Url
    }
}
[pscustomobject]@{
    provider = 'HP Client Management Script Library'
    packages = @($rows)
} | ConvertTo-Json -Depth 5 -Compress
'''


def hp_softpaqs(manufacturer: str) -> dict:
    if platform.system() != "Windows":
        raise DiscoveryError("HP catalogue discovery requires Windows.")
    if "hp" not in manufacturer.casefold() and "hewlett" not in manufacturer.casefold():
        raise DiscoveryError("HP catalogue discovery requires an HP computer.")
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", SCRIPT],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=240, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise DiscoveryError(f"HP catalogue scan failed: {exc}") from exc
    if result.returncode:
        raise DiscoveryError(result.stderr.strip() or "HP catalogue scan failed")
    try:
        data = json.loads(result.stdout.strip())
    except ValueError as exc:
        raise DiscoveryError("Invalid HP CMSL response") from exc
    if not isinstance(data, dict):
        raise DiscoveryError("Invalid HP CMSL payload")
    return {
        "provider": "HP CMSL / HP reference metadata",
        "packages": _as_list(data.get("packages")),
        "verified_for_device": False,
        "note": "Catalogue metadata only. No driver package downloaded; applicability, version and publisher require independent review.",
    }
