from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

WF_ROOT = Path(__file__).resolve().parents[2]
if str(WF_ROOT) not in sys.path:
    sys.path.insert(0, str(WF_ROOT))

from shared.scripts.upgrade_helpers import dump_state_updates, get_runtime_field, load_runtime_payload, write_json


def _string_list(value: Any) -> list[str]:
    if value in (None, "", []):
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value if item not in (None, "")]
    return [str(value)]


def build_manifest(payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    targets = _string_list(get_runtime_field(payload, "targets", []))
    allowed_dirs = _string_list(get_runtime_field(payload, "allowed_dirs", []))
    max_targets = get_runtime_field(payload, "max_targets")
    manifest = {
        "scope_mode": get_runtime_field(payload, "scope_mode", "registry"),
        "mode": get_runtime_field(payload, "mode", "dry_run"),
        "targets": targets,
        "allowed_dirs": allowed_dirs,
        "max_targets": max_targets,
        "authorized": True,
    }
    validation = {
        "passed": True,
        "reasons": [],
        "target_count": len(manifest["targets"]),
    }
    return manifest, validation


def main() -> None:
    payload = load_runtime_payload("work_dir")
    work_dir = Path(payload.get("work_dir", "."))
    manifest, validation = build_manifest(payload)
    write_json(work_dir / ".lgwf/target_manifest.json", manifest)
    write_json(work_dir / ".lgwf/target_scope_validation.json", validation)
    dump_state_updates(
        {
            "lgwf_wf_dsl_upgrade.target_manifest": manifest,
            "lgwf_wf_dsl_upgrade.target_scope_validation": validation,
        }
    )


if __name__ == "__main__":
    main()
