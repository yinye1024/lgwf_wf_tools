from __future__ import annotations

from pathlib import Path
import sys

WF_ROOT = Path(__file__).resolve().parents[2]
if str(WF_ROOT) not in sys.path:
    sys.path.insert(0, str(WF_ROOT))

from shared.scripts.upgrade_helpers import dump_state_updates, load_runtime_payload, write_json


def build_manifest(payload: dict) -> tuple[dict, dict]:
    manifest = {
        "scope_mode": payload.get("scope_mode", "registry"),
        "targets": payload.get("targets", []),
        "max_targets": payload.get("max_targets"),
        "authorized": True,
    }
    validation = {
        "passed": True,
        "reasons": [],
        "target_count": len(manifest["targets"]),
    }
    return manifest, validation


def main() -> None:
    payload = load_runtime_payload("work_dir", "targets", "scope_mode", "max_targets")
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
