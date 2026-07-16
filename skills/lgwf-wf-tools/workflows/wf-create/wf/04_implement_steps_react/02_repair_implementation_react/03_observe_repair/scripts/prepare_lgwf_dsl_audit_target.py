"""准备 TOOL 节点可审计的固定目标目录。"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any


AUDIT_TARGET_ROOT = Path(".lgwf") / "implementation_lgwf_dsl_audit_target"


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def resolve_target_package(root: Path) -> Path:
    context = read_json(root / ".lgwf" / "implementation_context.json")
    raw_target = str(context.get("target_package_abs", "")).strip()
    if raw_target:
        return Path(raw_target).resolve()
    raw_workspace = str(context.get("workspace_root", "")).strip()
    raw_root = str(context.get("target_package_root", "")).strip()
    if raw_workspace and raw_root:
        return (Path(raw_workspace).resolve() / raw_root).resolve()
    raise ValueError("implementation_context 缺少 target_package_abs 或 workspace_root/target_package_root")


def prepare_target(root: Path) -> dict[str, Any]:
    lgwf_dir = root / ".lgwf"
    target_abs = resolve_target_package(root)
    audit_target_abs = root / AUDIT_TARGET_ROOT

    if not audit_target_abs.resolve().is_relative_to(lgwf_dir.resolve()):
        raise ValueError(f"audit target 必须位于运行态 .lgwf 内: {audit_target_abs}")

    if audit_target_abs.exists():
        shutil.rmtree(audit_target_abs)
    audit_target_abs.parent.mkdir(parents=True, exist_ok=True)

    copied = target_abs.is_dir()
    if copied:
        shutil.copytree(target_abs, audit_target_abs)
    else:
        (audit_target_abs / "wf").mkdir(parents=True, exist_ok=True)
        (audit_target_abs / "wf" / "workflow.lgwf").write_text(
            "WORKFLOW missing_target;\nENTRY missing;\n",
            encoding="utf-8",
        )

    manifest = {
        "prepared": True,
        "copied": copied,
        "target_package_abs": str(target_abs),
        "audit_target_root": AUDIT_TARGET_ROOT.as_posix(),
        "tool_input": (AUDIT_TARGET_ROOT / "wf" / "workflow.lgwf").as_posix(),
    }
    write_json(lgwf_dir / "implementation_lgwf_dsl_audit_target_manifest.json", manifest)
    return manifest


def main() -> None:
    result = prepare_target(Path.cwd())
    print(json.dumps({"lgwf_wf_create.prepare_lgwf_dsl_audit_target_result": result}, ensure_ascii=False))


if __name__ == "__main__":
    main()
