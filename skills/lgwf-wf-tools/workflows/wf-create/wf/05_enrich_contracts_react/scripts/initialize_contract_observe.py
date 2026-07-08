"""初始化 Contract 补强阶段的 observe 状态。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def initialize(work_dir: Path) -> dict[str, Any]:
    lgwf_dir = work_dir / ".lgwf"
    implementation_context = read_json(lgwf_dir / "implementation_context.json")
    target_package_abs = str(implementation_context.get("target_package_abs", "")).strip()
    target_dirs = [target_package_abs] if target_package_abs else []
    observe = {
        "passed": False,
        "initialized": True,
        "reason": "Contract enrichment has not run yet.",
        "failures": ["尚未执行 Contract 补强和 audit observe"],
        "target_package_root": implementation_context.get("target_package_root", ""),
        "target_package_abs": target_package_abs,
    }
    write_json(lgwf_dir / "contract_observe.json", observe)
    return {
        "lgwf_wf_create.contract_observe": observe,
        "lgwf_wf_create.contract_target_dirs": target_dirs,
    }


def main() -> None:
    print(json.dumps(initialize(Path.cwd()), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
