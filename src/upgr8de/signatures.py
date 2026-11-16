"""Windows Authenticode inspection; never executes target files."""
from __future__ import annotations

import json
import platform
import subprocess
from pathlib import Path

from .windows import DiscoveryError

SCRIPT = r'''
$ErrorActionPreference = 'Stop'
$path = $args[0]
$sig = Get-AuthenticodeSignature -LiteralPath $path
$cert = $sig.SignerCertificate
[pscustomobject]@{
    status = [string]$sig.Status
    status_message = [string]$sig.StatusMessage
    signer_subject = if ($cert) { [string]$cert.Subject } else { $null }
    signer_thumbprint = if ($cert) { [string]$cert.Thumbprint } else { $null }
    signer_not_after = if ($cert) { $cert.NotAfter.ToString('o') } else { $null }
} | ConvertTo-Json -Compress
'''


def inspect_signature(path: str) -> dict:
    if platform.system() != "Windows":
        raise DiscoveryError("Authenticode inspection requires Windows.")
    target = Path(path).resolve(strict=True)
    if not target.is_file():
        raise DiscoveryError("Target must be a regular file")
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", SCRIPT, str(target)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=45, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise DiscoveryError(f"Signature inspection failed: {exc}") from exc
    if result.returncode:
        raise DiscoveryError(result.stderr.strip() or "Signature inspection failed")
    try:
        details = json.loads(result.stdout.strip())
    except ValueError as exc:
        raise DiscoveryError("Invalid Authenticode response") from exc
    return {
        "file": str(target),
        **details,
        "signature_valid": details.get("status") == "Valid",
        "publisher_authorized": "not_checked",
        "note": "Valid signature alone does not prove OEM authorization or device compatibility.",
    }
