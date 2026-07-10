from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


SHARED_SCRIPTS = Path(__file__).resolve().parents[2] / "shared" / "scripts"
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))

from dsl_upgrade_common import load_json, write_json


def build_scope_confirmation_context(root: Path) -> dict[str, Any]:
    manifest = load_json(root / ".lgwf" / "target_manifest.json", {})
    validation = load_json(root / ".lgwf" / "target_scope_validation.json", {})
    request = manifest.get("request", {}) if isinstance(manifest, dict) else {}
    targets = manifest.get("authorized_targets", []) if isinstance(manifest, dict) else []
    target_items: list[dict[str, Any]] = []
    for target in targets:
        if not isinstance(target, dict):
            continue
        target_items.append(
            {
                "path": str(target.get("resolved_path", "")).strip(),
                "raw_path": str(target.get("raw_path", "")).strip(),
                "pre_hash": str(target.get("pre_hash", "")).strip(),
            }
        )
    context = {
        "title": "确认 DSL 升级目标范围",
        "mode": str(request.get("mode", "dry_run")),
        "scope_mode": str(request.get("scope_mode", "explicit")),
        "target_count": len(target_items),
        "targets": target_items,
        "validation": validation if isinstance(validation, dict) else {},
        "impact": (
            "approve 后会按目标列表逐个运行 audit，并在 mode=apply 时允许 Codex "
            "只修改当前授权 .lgwf 文件；reject 会跳过修复并进入 summary。"
        ),
        "options": ["approve", "reject"],
        "recommended_decision": "approve" if validation.get("passed") and target_items else "reject",
    }
    write_json(root / ".lgwf" / "scope_confirmation_context.json", context)
    return context


def main() -> None:
    context = build_scope_confirmation_context(Path.cwd())
    print(json.dumps({"wf_dsl_upgrade.scope_confirmation_context": context}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
