from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from dsl_upgrade_common import compute_sha256, path_is_authorized, write_json


def _read_payload() -> dict[str, Any]:
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    data = json.loads(raw)
    return data if isinstance(data, dict) else {}


def build_repair_context(root: Path, target: dict[str, Any]) -> dict[str, Any]:
    target_path = Path(str(target.get("path", ""))).expanduser().resolve()
    allowed_dirs = [Path(str(item)).expanduser().resolve() for item in target.get("allowed_dirs", [])]
    authorized = target_path.exists() and target_path.is_file() and path_is_authorized(target_path, allowed_dirs)
    current_hash = compute_sha256(target_path) if target_path.exists() and target_path.is_file() else ""
    context = {
        "target_id": str(target.get("target_id", "")),
        "path": str(target_path),
        "mode": str(target.get("mode", "dry_run")),
        "authorized": authorized,
        "allowed_dirs": [str(item) for item in allowed_dirs],
        "target_files": [str(target_path)],
        "target_dirs": [str(target_path.parent.resolve())],
        "pre_hash": str(target.get("pre_hash", "") or ""),
        "current_hash": current_hash,
        "instructions": [
            "只处理当前 path 指向的 .lgwf 文件。",
            "mode=dry_run 时不得修改目标文件。",
            "mode=apply 时也不得修改 target_files 之外的文件。",
            "优先做满足 audit diagnostics 的最小 DSL 修复。",
        ],
    }
    write_json(root / ".lgwf" / "current_target_context.json", context)
    return context


def main() -> None:
    context = build_repair_context(Path.cwd(), _read_payload())
    print(
        json.dumps(
            {
                "wf_dsl_upgrade.repair_context": context,
                "wf_dsl_upgrade.target_files": context["target_files"],
                "wf_dsl_upgrade.target_dirs": context["target_dirs"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
