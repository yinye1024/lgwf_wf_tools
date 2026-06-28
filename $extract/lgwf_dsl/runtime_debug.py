from __future__ import annotations

import hashlib
import importlib.metadata
import pathlib
from typing import Any

import lgwf_dsl
import lgwf_dsl.artifact_contracts as artifact_contracts_module
import lgwf_dsl.parser as parser_module


def collect_runtime_debug(
    *,
    bundled_wheel: str | pathlib.Path | None = None,
) -> dict[str, Any]:
    wheel_path = pathlib.Path(bundled_wheel).resolve() if bundled_wheel else None
    data: dict[str, Any] = {
        "python_package_version": _package_version("lgwf"),
        "lgwf_dsl_file": str(pathlib.Path(lgwf_dsl.__file__).resolve()) if lgwf_dsl.__file__ else None,
        "parser_file": str(pathlib.Path(parser_module.__file__).resolve()),
        "artifact_contracts_file": str(pathlib.Path(artifact_contracts_module.__file__).resolve()),
        "supports_flow_block": hasattr(parser_module.Parser, "_parse_flow_block"),
        "supports_output_file": "OUTPUT_FILE" in getattr(parser_module.Parser, "TOP_LEVEL_STATEMENTS", ())
        or _parser_source_contains("OUTPUT_FILE"),
        "artifact_contract_auditor_enabled": hasattr(artifact_contracts_module, "ArtifactContractAuditor"),
    }
    if wheel_path is not None:
        data["bundled_wheel"] = str(wheel_path)
        data["bundled_wheel_exists"] = wheel_path.is_file()
        if wheel_path.is_file():
            data["bundled_wheel_sha256"] = _sha256(wheel_path)
    return data


def _package_version(package_name: str) -> str | None:
    try:
        return importlib.metadata.version(package_name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _parser_source_contains(needle: str) -> bool:
    try:
        return needle in pathlib.Path(parser_module.__file__).read_text(encoding="utf-8")
    except OSError:
        return False


def _sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
