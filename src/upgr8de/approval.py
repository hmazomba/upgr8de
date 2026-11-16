"""Deterministic download approval from background job evidence, never AI prose."""
from __future__ import annotations

import re

from .agent import read_job
from .downloads import download_package, validate_source


class ApprovalError(ValueError):
    pass


def approved_candidate(job_id: str, candidate_index: int) -> dict:
    if candidate_index < 0:
        raise ApprovalError("Invalid candidate index")
    job = read_job(job_id)
    if job.get("status") != "completed":
        raise ApprovalError("AI job not complete")
    candidates = job.get("verified_candidates", [])
    if not isinstance(candidates, list) or candidate_index >= len(candidates):
        raise ApprovalError("No verified candidate at index")
    candidate = candidates[candidate_index]
    if not isinstance(candidate, dict):
        raise ApprovalError("Malformed candidate")
    if (candidate.get("status") != "exact_hardware_os_match"
            or candidate.get("source_verified") is not True
            or candidate.get("hardware_id_verified") is not True
            or candidate.get("os_verified") is not True
            or not re.fullmatch(r"[0-9a-fA-F]{64}", str(candidate.get("sha256", "")))):
        raise ApprovalError("Candidate lacks required independent compatibility and hash evidence")
    validate_source(candidate["url"], candidate["vendor"])
    return candidate


def download_approved(job_id: str, candidate_index: int, output_dir: str) -> dict:
    candidate = approved_candidate(job_id, candidate_index)
    return download_package(candidate["url"], candidate["vendor"], output_dir,
                            sha256=candidate["sha256"])
