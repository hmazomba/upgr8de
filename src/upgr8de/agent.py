"""Opt-in background AI assessment using OpenAI-compatible chat completions.

AI never invents download URLs, downloads packages, or installs drivers.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import uuid
from pathlib import Path
from urllib.parse import urlsplit

DEFAULT_ENDPOINT = "https://api.openai.com/v1"
MAX_PAYLOAD = 250_000


class AgentError(ValueError):
    pass


def config() -> dict:
    endpoint = os.environ.get("UPGR8DE_AI_BASE_URL", DEFAULT_ENDPOINT).rstrip("/")
    parts = urlsplit(endpoint)
    if (parts.scheme != "https" or not parts.hostname or parts.username or parts.password
            or parts.query or parts.fragment or parts.port not in (None, 443)):
        if not (os.environ.get("UPGR8DE_AI_ALLOW_HTTP_LOCAL") == "1"
                and parts.scheme == "http" and parts.hostname in ("localhost", "127.0.0.1")
                and parts.port is not None):
            raise AgentError("AI base URL must be HTTPS (or explicitly enabled loopback HTTP)")
    model = os.environ.get("UPGR8DE_AI_MODEL", "")
    if not model or not re.fullmatch(r"[A-Za-z0-9_./:-]{1,150}", model):
        raise AgentError("Set UPGR8DE_AI_MODEL")
    if not os.environ.get("UPGR8DE_AI_API_KEY"):
        raise AgentError("Set UPGR8DE_AI_API_KEY")
    return {"endpoint": endpoint, "model": model}


def job_root() -> Path:
    root = Path(os.environ.get("UPGR8DE_JOB_DIR", str(Path.home() / ".upgr8de" / "jobs"))).resolve()
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    return root


def submit_background(evidence: dict, *, catalogue_path: str | None = None,
                      catalogue_sha256: str | None = None) -> dict:
    settings = config()
    raw = json.dumps(evidence, ensure_ascii=False)
    if len(raw.encode("utf-8")) > MAX_PAYLOAD:
        raise AgentError("Evidence exceeds AI request limit")
    job_id = uuid.uuid4().hex
    path = job_root() / f"{job_id}.json"
    payload = {"id": job_id, "status": "queued", "evidence": evidence, "model": settings["model"]}
    if catalogue_path and catalogue_sha256:
        from .verified_candidates import verified_catalogue_candidates
        verified = verified_catalogue_candidates(catalogue_path, catalogue_sha256,
                                                 evidence.get("devices", []), evidence.get("system", {}))
        payload["verified_candidates"] = verified
        payload["catalogue_sha256"] = catalogue_sha256.lower()
    with path.open("x", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False)
    try:
        flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
        subprocess.Popen(
            [sys.executable, "-m", "upgr8de.agent_worker", str(path)],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            close_fds=True, creationflags=flags, start_new_session=(os.name != "nt"),
        )
    except OSError as exc:
        path.unlink(missing_ok=True)
        raise AgentError(f"Unable to start background worker: {exc}") from exc
    return {"job_id": job_id, "status": "queued", "job_file": str(path), "model": settings["model"]}


def read_job(job_id: str) -> dict:
    if not re.fullmatch(r"[a-f0-9]{32}", job_id):
        raise AgentError("Invalid job ID")
    path = job_root() / f"{job_id}.json"
    if not path.is_file():
        raise AgentError("Job not found")
    return json.loads(path.read_text(encoding="utf-8"))
