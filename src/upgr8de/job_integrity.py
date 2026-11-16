"""Integrity seal for job-derived download approvals.

This detects edits to job records after submission, not compromise by same-OS user.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
from pathlib import Path

from .agent import job_root


def _key() -> bytes:
    path = job_root() / ".approval-key"
    try:
        fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        pass
    else:
        with os.fdopen(fd, "wb") as stream:
            stream.write(secrets.token_bytes(32))
    key = path.read_bytes()
    if len(key) != 32:
        raise ValueError("Invalid local approval key")
    return key


def _canonical(job: dict) -> bytes:
    fields = {"id": job.get("id"), "verified_candidates": job.get("verified_candidates", []),
              "catalogue_sha256": job.get("catalogue_sha256")}
    return json.dumps(fields, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def seal(job: dict) -> None:
    job["approval_seal"] = hmac.new(_key(), _canonical(job), hashlib.sha256).hexdigest()


def verify(job: dict) -> bool:
    expected = job.get("approval_seal")
    return isinstance(expected, str) and hmac.compare_digest(
        expected, hmac.new(_key(), _canonical(job), hashlib.sha256).hexdigest()
    )
