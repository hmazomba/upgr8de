"""Conservative OEM package downloader. Downloads only; never executes or installs."""
from __future__ import annotations

import hashlib
import os
import re
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit, unquote

ALLOWED = {
    "dell": {"downloads.dell.com", "dl.dell.com"},
    "hp": {"ftp.hp.com", "hpia.hpcloud.hp.com"},
    "lenovo": {"download.lenovo.com"},
    "asus": {"dlcdnets.asus.com"},
}
EXTENSIONS = {".cab", ".zip", ".exe", ".msi"}
MAX_BYTES = 1024 * 1024 * 1024
HASH_RE = re.compile(r"^[a-fA-F0-9]{64}$")


class DownloadError(ValueError):
    pass


def validate_source(url: str, vendor: str) -> str:
    vendor = vendor.lower()
    if vendor not in ALLOWED:
        raise DownloadError("Unsupported OEM; choose dell, hp, lenovo or asus")
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError as exc:
        raise DownloadError("Invalid URL") from exc
    if (parts.scheme != "https" or parts.hostname not in ALLOWED[vendor]
            or port not in (None, 443) or parts.username or parts.password
            or parts.query or parts.fragment or "\\" in url):
        raise DownloadError("URL must be direct HTTPS on approved OEM host without query, credentials or redirect")
    filename = unquote(parts.path.rsplit("/", 1)[-1])
    if (not filename or filename in (".", "..") or "/" in filename or "\\" in filename
            or any(ord(ch) < 32 for ch in filename) or Path(filename).suffix.lower() not in EXTENSIONS):
        raise DownloadError("Unsupported or unsafe package filename")
    return filename


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise DownloadError("Redirect blocked; cannot validate destination")


def download_package(url: str, vendor: str, output_dir: str, *, sha256: str | None = None,
                     max_bytes: int = MAX_BYTES) -> dict:
    filename = validate_source(url, vendor)
    if sha256 is not None and not HASH_RE.fullmatch(sha256):
        raise DownloadError("SHA-256 must be 64 hexadecimal characters")
    if not 0 < max_bytes <= MAX_BYTES:
        raise DownloadError("Invalid download size limit")
    destination = Path(output_dir).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    final = destination / filename
    if final.exists():
        raise DownloadError("Destination already exists; refusing overwrite")
    opener = urllib.request.build_opener(NoRedirect())
    temp_path = None
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "upgr8de/0.1"})
        with opener.open(request, timeout=60) as response:
            length = response.headers.get("Content-Length")
            if length and int(length) > max_bytes:
                raise DownloadError("Package exceeds size limit")
            fd, temp_path = tempfile.mkstemp(prefix=".upgr8de-", suffix=".part", dir=destination)
            digest = hashlib.sha256()
            size = 0
            with os.fdopen(fd, "wb") as output:
                while chunk := response.read(1024 * 1024):
                    size += len(chunk)
                    if size > max_bytes:
                        raise DownloadError("Package exceeds size limit")
                    digest.update(chunk)
                    output.write(chunk)
        actual = digest.hexdigest()
        if sha256 and actual != sha256.lower():
            raise DownloadError("SHA-256 mismatch; discarded downloaded package")
        # Atomic same-directory hard link: never expose partial destination or overwrite.
        os.link(temp_path, final)
        return {
            "path": str(final), "vendor": vendor.lower(), "source_url": url,
            "size_bytes": size, "sha256": actual,
            "hash_verified": sha256 is not None,
            "signature_verified": False,
            "status": "hash_verified" if sha256 else "downloaded_unverified",
            "note": "No installation. Independently verify publisher signature and model/OS compatibility.",
        }
    except (OSError, urllib.error.URLError, ValueError) as exc:
        if isinstance(exc, DownloadError):
            raise
        raise DownloadError(f"Download failed: {exc}") from exc
    finally:
        if temp_path:
            try:
                os.unlink(temp_path)
            except FileNotFoundError:
                pass
