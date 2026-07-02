from __future__ import annotations

import json
from pathlib import Path
from typing import Any


from _paths import FACADE_ROOT, SELF_IMPROVE_ROOT
MANIFEST_PATH = SELF_IMPROVE_ROOT / "manifest.json"


def read_manifest() -> dict[str, Any]:
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError("manifest root must be object")
    return data


def validate_manifest() -> list[str]:
    issues: list[str] = []
    manifest = read_manifest()
    entrypoint = manifest.get("entrypoint")
    if not isinstance(entrypoint, str) or not (SELF_IMPROVE_ROOT / entrypoint).is_file():
        issues.append(f"entrypoint missing: {entrypoint}")

    commands = manifest.get("commands")
    if not isinstance(commands, dict) or not commands:
        issues.append("commands must be a non-empty object")
    else:
        for name, relative in commands.items():
            if not isinstance(name, str) or not isinstance(relative, str):
                issues.append("command names and paths must be strings")
                continue
            if not (SELF_IMPROVE_ROOT / relative).is_file():
                issues.append(f"command script missing: {name} -> {relative}")

    protected = manifest.get("protected_local_roots")
    if not isinstance(protected, list) or ".local/self-improve" not in protected:
        issues.append("protected_local_roots must include .local/self-improve")

    policy = manifest.get("release_policy")
    if not isinstance(policy, dict) or ".local" not in policy.get("must_preserve", []):
        issues.append("release_policy.must_preserve must include .local")

    local_state_root = manifest.get("local_state_root")
    if local_state_root != ".local/self-improve":
        issues.append("local_state_root must be .local/self-improve")

    if not (FACADE_ROOT / ".gitignore").is_file():
        issues.append(".gitignore missing")
    else:
        gitignore = (FACADE_ROOT / ".gitignore").read_text(encoding="utf-8")
        if ".local/" not in gitignore:
            issues.append(".gitignore must ignore .local/")
    required_support_files = [
        SELF_IMPROVE_ROOT / "overrides" / "schema.json",
        SELF_IMPROVE_ROOT / "workflow-health" / "schema.json",
        SELF_IMPROVE_ROOT / "workflow-health" / "baseline.json",
    ]
    for path in required_support_files:
        if not path.is_file():
            issues.append(f"required support file missing: {path.relative_to(SELF_IMPROVE_ROOT).as_posix()}")
    return issues


def main() -> int:
    issues = validate_manifest()
    print(json.dumps({"passed": not issues, "issues": issues}, ensure_ascii=False))
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
