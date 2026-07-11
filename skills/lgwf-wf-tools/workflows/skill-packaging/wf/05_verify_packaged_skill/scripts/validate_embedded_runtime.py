"""校验 embedded runtime 与本地 runner。"""

from __future__ import annotations

import json
import sys
from pathlib import Path


SHARED_SCRIPTS = Path(__file__).resolve().parents[2] / "shared" / "scripts"
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))

from packaging_common import read_stdin_object


def main() -> None:
    context = read_stdin_object()
    if not context:
        raise ValueError("package_validation_context 不能为空")

    output_skill_abs = Path(str(context["output_skill_abs"]))
    runtime_dir = output_skill_abs / "vendor" / "lgwf-client-assist"
    runner_path = output_skill_abs / "scripts" / "run_local_lgwf_workflow.py"

    runtime_issues: list[str] = []
    required_runtime_files = [
        runtime_dir / "AGENTS.md",
        runtime_dir / "scripts" / "lgwf.py",
    ]
    for path in required_runtime_files:
        if not path.is_file():
            runtime_issues.append(f"缺少 embedded runtime 文件：{path.relative_to(output_skill_abs).as_posix()}")

    if runner_path.is_file():
        runner_text = runner_path.read_text(encoding="utf-8-sig")
        if 'vendor" / "lgwf-client-assist" / "scripts" / "lgwf.py"' not in runner_text:
            runtime_issues.append("local runner 没有指向打包产物内的 vendor runtime")
        if '"wf/workflow.lgwf"' not in runner_text:
            runtime_issues.append("local runner 没有固定运行 wf/workflow.lgwf")
        if '"ws"' not in runner_text:
            runtime_issues.append("local runner 没有固定使用 ws 作为 work dir")
    else:
        runtime_issues.append("缺少 local runner 文件")

    issues = list(context.get("issues", []))
    issues.extend(runtime_issues)
    context["issues"] = issues
    context.setdefault("checks", {})["embedded_runtime"] = {
        "runtime_dir": str(runtime_dir),
        "runner_path": str(runner_path),
        "ok": not runtime_issues,
        "issues": runtime_issues,
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

