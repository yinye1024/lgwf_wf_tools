"""校验 PACKAGING_MANIFEST.json。"""

from __future__ import annotations

import json
import sys
from pathlib import Path


SHARED_SCRIPTS = Path(__file__).resolve().parents[2] / "shared" / "scripts"
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))

from packaging_common import read_json, read_stdin_object


def main() -> None:
    context = read_stdin_object()
    if not context:
        raise ValueError("package_validation_context 不能为空")

    output_skill_abs = Path(str(context["output_skill_abs"]))
    manifest_path = output_skill_abs / "PACKAGING_MANIFEST.json"
    manifest = read_json(manifest_path)

    issues = list(context.get("issues", []))
    manifest_issues: list[str] = []
    for key in context.get("required_manifest_keys", []):
        if key not in manifest:
            manifest_issues.append(f"manifest 缺少必需字段：{key}")
    expected_name = Path(str(context["source_skill_abs"])).name
    if manifest.get("source_skill_name") != expected_name:
        manifest_issues.append("manifest.source_skill_name 与源 skill 名称不一致")
    if manifest.get("runtime_relative_path") != "vendor/lgwf-client-assist":
        manifest_issues.append("manifest.runtime_relative_path 必须是 vendor/lgwf-client-assist")
    if manifest.get("local_runner") != "scripts/run_local_lgwf_workflow.py":
        manifest_issues.append("manifest.local_runner 必须指向 scripts/run_local_lgwf_workflow.py")

    issues.extend(manifest_issues)
    context["issues"] = issues
    context["manifest"] = manifest
    context.setdefault("checks", {})["manifest"] = {
        "path": str(manifest_path),
        "ok": not manifest_issues,
        "issues": manifest_issues,
    }
    print(
        json.dumps(
            {"skill_packaging.package_validation_context": context},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

