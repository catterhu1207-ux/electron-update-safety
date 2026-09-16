from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import uuid


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(_extended(path)).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _inside(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _extended(path: Path) -> str:
    value = str(path.resolve())
    return "\\\\?\\" + value if os.name == "nt" and not value.startswith("\\\\?\\") else value


def check_manifest(source: Path, manifest_path: Path, consumer_root: Path) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    if manifest.get("schema_version") != 1 or not isinstance(manifest.get("version"), str):
        raise ValueError("unsupported_or_incomplete_manifest")
    expected_files = manifest.get("source_files")
    consumers = manifest.get("required_consumers")
    if not isinstance(expected_files, dict) or not expected_files:
        raise ValueError("source_files_required")
    if not isinstance(consumers, dict):
        raise ValueError("required_consumers_required")

    files = []
    errors = []
    for relative, expected in expected_files.items():
        path = source / relative
        actual = _sha256(path) if Path(_extended(path)).is_file() else None
        files.append({"path": relative, "expected_sha256": expected, "actual_sha256": actual})
        if actual != expected:
            errors.append(f"source_digest_mismatch:{relative}")

    consumer_results = []
    for relative, tokens in consumers.items():
        path = consumer_root / relative
        text = path.read_text(encoding="utf-8", errors="strict") if path.is_file() else ""
        missing = [token for token in tokens if token not in text]
        consumer_results.append({"path": relative, "missing_tokens": missing})
        if missing or not path.is_file():
            errors.append(f"consumer_contract_failed:{relative}")

    descriptor = manifest.get("backend_descriptor")
    descriptor_result = None
    if descriptor:
        path = source / descriptor["path"]
        actual = _sha256(path) if Path(_extended(path)).is_file() else None
        descriptor_result = {"path": descriptor["path"], "actual_sha256": actual}
        if actual != descriptor["sha256"]:
            errors.append("backend_descriptor_mismatch")

    return {
        "schema_version": 1,
        "status": "passed" if not errors else "blocked",
        "version": manifest["version"],
        "source": str(source.resolve()),
        "files": files,
        "consumers": consumer_results,
        "backend_descriptor": descriptor_result,
        "errors": errors,
        "content_logged": False,
    }


def stage_source(source: Path, work_root: Path, check: dict) -> dict:
    source = source.resolve()
    work_root = work_root.resolve()
    if check.get("status") != "passed":
        raise ValueError("preflight_not_passed")
    if _inside(work_root, source) or _inside(source, work_root):
        raise ValueError("source_and_work_root_must_not_be_nested")
    attempt = work_root / f"attempt-{uuid.uuid4().hex}"
    target = attempt / "source"
    attempt.mkdir(parents=True, exist_ok=False)
    shutil.copytree(_extended(source), _extended(target), symlinks=False)
    for row in check["files"]:
        if _sha256(target / row["path"]) != row["expected_sha256"]:
            raise RuntimeError(f"staged_digest_mismatch:{row['path']}")
    result = {**check, "stage_status": "pristine", "stage_directory": str(attempt)}
    (attempt / "source-identity.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result
