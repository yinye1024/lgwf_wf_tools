from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared"))

from prompt_upgrade_common import lgwf_dir, output_state, write_json


ARTIFACT_ROOT = ".lgwf/prompt_upgrade"


def ensure_bundled_client_dir() -> Path:
    return Path(__file__).resolve().parents[5] / "vendor" / "lgwf-client-assist"


def candidate_skill_dirs() -> list[Path]:
    candidates: list[Path] = []
    for env_name in ("LGWF_CLIENT_ASSIST", "LGWF_CLIENT_ASSIST_SKILL_DIR"):
        configured = os.environ.get(env_name)
        if configured:
            candidates.append(Path(configured).expanduser())
    if not candidates:
        candidates.append(ensure_bundled_client_dir())
    return candidates


def find_lgwf_client_assist(candidates: list[Path] | None = None) -> dict[str, Any]:
    checked: list[str] = []
    for candidate in candidates or candidate_skill_dirs():
        marker = candidate / "AGENTS.md"
        checked.append(str(marker))
        if marker.is_file():
            return {
                "passed": True,
                "skill_dir": str(candidate),
                "skill_md": str(marker),
                "checked": checked,
                "reason": "",
            }
    return {
        "passed": False,
        "skill_dir": "",
        "skill_md": "",
        "checked": checked,
        "reason": "未检测到本地 bundled lgwf-client-assist。请先运行 scripts/init_lgwf_wf_agent.py 从临时 zip 同步 vendor，或确认 vendor/lgwf-client-assist 已随 facade 分发。",
    }


def main() -> None:
    out_dir = lgwf_dir() / "prompt_upgrade"
    result = find_lgwf_client_assist()
    result["artifact_root"] = ARTIFACT_ROOT
    write_json(out_dir / "environment_check.json", result)
    if not result["passed"]:
        raise RuntimeError(result["reason"])
    output_state({"environment_check": result})


if __name__ == "__main__":
    main()
