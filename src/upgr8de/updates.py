"""Read-only Windows Update Agent driver offer discovery.

Windows Update performs its own applicability checks. An offered update is NOT
proof that its version is newer than a specific installed driver.
"""
from __future__ import annotations

import json
import platform
import subprocess

from .windows import DiscoveryError, _as_list

SCRIPT = r'''
$ErrorActionPreference = 'Stop'
$session = New-Object -ComObject Microsoft.Update.Session
$session.ClientApplicationID = 'upgr8de read-only driver discovery'
$searcher = $session.CreateUpdateSearcher()
$result = $searcher.Search("IsInstalled=0 and Type='Driver' and IsHidden=0")
$items = @()
for ($i = 0; $i -lt $result.Updates.Count; $i++) {
    $u = $result.Updates.Item($i)
    $kb = @()
    if ($null -ne $u.KBArticleIDs) { $kb = @($u.KBArticleIDs) }
    $driverHardwareID = $null
    $driverVersion = $null
    $driverManufacturer = $null
    try { $driverHardwareID = [string]$u.DriverHardwareID } catch {}
    try { $driverVersion = [string]$u.DriverVersion } catch {}
    try { $driverManufacturer = [string]$u.DriverManufacturer } catch {}
    $items += [pscustomobject]@{
        driver_hardware_id = $driverHardwareID
        driver_version = $driverVersion
        driver_manufacturer = $driverManufacturer
        title = [string]$u.Title
        update_id = [string]$u.Identity.UpdateID
        revision = [int]$u.Identity.RevisionNumber
        description = [string]$u.Description
        kb_ids = $kb
        is_downloaded = [bool]$u.IsDownloaded
        requires_reboot = [bool]$u.RebootRequired
    }
}
[pscustomobject]@{
    source = 'Windows Update Agent'
    result_code = [int]$result.ResultCode
    updates = @($items)
} | ConvertTo-Json -Depth 6 -Compress
'''


def available_driver_offers() -> dict:
    """Ask Windows Update Agent for applicable, not-installed driver offers.

    Does not download, accept EULAs, or install updates. May contact configured
    Windows Update / WSUS service and may take time.
    """
    if platform.system() != "Windows":
        raise DiscoveryError("Windows Update detection requires Windows.")
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", SCRIPT],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=180, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise DiscoveryError(f"Windows Update scan failed: {exc}") from exc
    if result.returncode:
        raise DiscoveryError(result.stderr.strip() or "Windows Update scan failed")
    try:
        payload = json.loads(result.stdout.strip())
    except (ValueError, json.JSONDecodeError) as exc:
        raise DiscoveryError("Invalid Windows Update response") from exc
    if payload.get("result_code") != 2:
        raise DiscoveryError(f"Windows Update scan incomplete (result code {payload.get('result_code')})")
    return {
        "source": "Windows Update Agent (configured system update service)",
        "updates": _as_list(payload.get("updates")),
        "comparison": "OS-offered drivers; no installed-version comparison performed",
        "note": "Not all OEM driver updates are published through Windows Update. No packages downloaded or installed.",
    }
