"""Windows PnP discovery via read-only PowerShell CIM queries."""
from __future__ import annotations

import json
import platform
import subprocess


class DiscoveryError(RuntimeError):
    """Device discovery could not finish."""


POWERSHELL = r'''
$ErrorActionPreference = 'Stop'
$devices = @(Get-CimInstance Win32_PnPEntity | Select-Object Name, PNPDeviceID, DeviceID, HardwareID, Manufacturer, Service, Status, ConfigManagerErrorCode)
$drivers = @(Get-CimInstance Win32_PnPSignedDriver | Select-Object DeviceID, DriverVersion, DriverDate, DriverProviderName, InfName, IsSigned)
[pscustomobject]@{ devices = $devices; drivers = $drivers } | ConvertTo-Json -Depth 6 -Compress
'''


def _as_list(value: object) -> list[dict]:
    if value is None:
        return []
    if isinstance(value, dict):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []


def discover() -> list[dict]:
    if platform.system() != 'Windows':
        raise DiscoveryError('Windows required for MVP. Linux and macOS support planned.')
    try:
        completed = subprocess.run(
            ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', POWERSHELL],
            capture_output=True, text=True, timeout=90, check=False,
            encoding='utf-8', errors='replace',
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise DiscoveryError(f'PowerShell discovery failed: {exc}') from exc
    if completed.returncode != 0:
        raise DiscoveryError(completed.stderr.strip() or 'PowerShell discovery failed')
    try:
        payload = json.loads(completed.stdout.strip())
    except (json.JSONDecodeError, ValueError) as exc:
        raise DiscoveryError('Invalid JSON returned by PowerShell') from exc
    by_id = {
        str(x.get('DeviceID') or '').upper(): x
        for x in _as_list(payload.get('drivers'))
        if x.get('DeviceID')
    }
    records = []
    for device in _as_list(payload.get('devices')):
        device_id = str(device.get('PNPDeviceID') or device.get('DeviceID') or '')
        driver = by_id.get(device_id.upper(), {})
        error_code = device.get('ConfigManagerErrorCode')
        records.append({
            'name': device.get('Name') or 'Unknown device',
            'hardware_id': device_id,
            'hardware_ids': [str(x) for x in (device.get('HardwareID') or [])] if isinstance(device.get('HardwareID'), list) else ([str(device['HardwareID'])] if device.get('HardwareID') else []),
            'manufacturer': device.get('Manufacturer'),
            'status': device.get('Status'),
            'problem_code': error_code,
            'driver_provider': driver.get('DriverProviderName'),
            'driver_version': driver.get('DriverVersion'),
            'driver_date': driver.get('DriverDate'),
            'driver_inf': driver.get('InfName'),
            'driver_signed': driver.get('IsSigned'),
            'missing_driver': error_code == 28,
        })
    return sorted(records, key=lambda r: str(r['name']).casefold())
