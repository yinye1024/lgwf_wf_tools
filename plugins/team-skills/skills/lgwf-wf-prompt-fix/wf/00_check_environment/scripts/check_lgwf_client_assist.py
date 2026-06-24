from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared"))

from prompt_fix_common import lgwf_dir, output_state, write_json


ARTIFACT_ROOT = ".lgwf/prompt_acceptance"


def candidate_skill_dirs() -> list[Path]:
    candidates: list[Path] = []
    for env_name in ("LGWF_CLIENT_ASSIST", "LGWF_CLIENT_ASSIST_SKILL_DIR"):
        configured = os.environ.get(env_name)
        if configured:
            candidates.append(Path(configured).expanduser())

    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        candidates.append(Path(codex_home).expanduser() / "skills" / "lgwf-client-assist")

    candidates.append(Path.home() / ".codex" / "skills" / "lgwf-client-assist")
    return candidates


def find_lgwf_client_assist(candidates: list[Path] | None = None) -> dict[str, Any]:
    checked: list[str] = []
    for candidate in candidates or candidate_skill_dirs():
        skill_md = candidate / "SKILL.md"
        checked.append(str(skill_md))
        if skill_md.is_file():
            return {
                "passed": True,
                "skill_dir": str(candidate),
                "skill_md": str(skill_md),
                "checked": checked,
                "reason": "",
            }
    return {
        "passed": False,
        "skill_dir": "",
        "skill_md": "",
        "checked": checked,
        "reason": "未检测到已安装的 lgwf-client-assist skill。请先在当前 Codex 环境安装或启用 lgwf-client-assist，然后重新启动 lgwf_wf_prompt_fix。",
    }


def main() -> None:
    out_dir = lgwf_dir() / "prompt_acceptance"
    result = find_lgwf_client_assist()
    result["artifact_root"] = ARTIFACT_ROOT
    write_json(out_dir / "environment_check.json", result)
    if not result["passed"]:
        raise RuntimeError(result["reason"])
    output_state({"environment_check": result})


if __name__ == "__main__":
    main()
