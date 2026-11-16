"""Read-only Windows computer identity discovery for OEM support routing."""
from __future__ import annotations

import json
import platform
import subprocess

from .windows import DiscoveryError

SCRIPT = r'''
$ErrorActionPreference = 'Stop'
$system = Get-CimInstance Win32_ComputerSystem
$product = Get-CimInstance Win32_ComputerSystemProduct
$os = Get-CimInstance Win32_OperatingSystem
[pscustomobject]@{
    manufacturer = [string]$system.Manufacturer
    model = [string]$system.Model
    product_name = [string]$product.Name
    sku = [string]$system.SystemSKUNumber
    os_caption = [string]$os.Caption
    os_version = [string]$os.Version
    os_build = [string]$os.BuildNumber
    architecture = [string]$os.OSArchitecture
} | ConvertTo-Json -Compress
'''


def detect_system() -> dict:
    """Do not collect serial numbers, UUIDs or service tags."""
    if platform.system() != "Windows":
        raise DiscoveryError("OEM detection requires Windows.")
    try:
        completed = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", SCRIPT],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=45, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise DiscoveryError(f"OEM detection failed: {exc}") from exc
    if completed.returncode:
        raise DiscoveryError(completed.stderr.strip() or "OEM detection failed")
    try:
        data = json.loads(completed.stdout.strip())
    except ValueError as exc:
        raise DiscoveryError("Invalid OEM detection response") from exc
    if not isinstance(data, dict):
        raise DiscoveryError("Invalid OEM detection payload")
    return data
