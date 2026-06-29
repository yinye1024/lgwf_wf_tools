from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared"))

from prompt_fix_common import lgwf_dir, output_state, write_json


ARTIFACT_ROOT = ".lgwf/prompt_acceptance"
REFERENCE_CONTEXT_ROOT = "reference_context"
REFERENCE_FILES = (
    ("AGENTS.md", "AGENTS.md"),
    ("references/prompt-assist/guide.md", "prompt-assist/guide.md"),
    ("references/prompt-assist/shared-rules.md", "prompt-assist/shared-rules.md"),
    ("references/prompt-assist/prompt-audit-checklist.md", "prompt-assist/prompt-audit-checklist.md"),
    ("references/prompt-assist/draft-prompt.md", "prompt-assist/draft-prompt.md"),
    ("references/prompt-assist/action-prompt.md", "prompt-assist/action-prompt.md"),
    ("references/prompt-assist/audit-prompt.md", "prompt-assist/audit-prompt.md"),
    ("references/prompt-assist/normal-prompt.md", "prompt-assist/normal-prompt.md"),
)


def ensure_bundled_client_dir() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        candidate = parent / "vendor" / "lgwf-client-assist"
        if (candidate / "AGENTS.md").is_file():
            return candidate
    return current.parents[5] / "vendor" / "lgwf-client-assist"


def candidate_skill_dirs() -> list[Path]:
    return [ensure_bundled_client_dir()]


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
        "reason": "未检测到本地 bundled lgwf-client-assist。请先运行 scripts/init_lgwf_wf_tools.py 从临时 zip 同步 vendor，或确认 vendor/lgwf-client-assist 已随 facade 分发。",
    }


def prepare_reference_context(skill_dir: Path, out_dir: Path) -> dict[str, Any]:
    context_root = out_dir / REFERENCE_CONTEXT_ROOT
    if context_root.exists():
        shutil.rmtree(context_root)
    copied: list[str] = []
    missing: list[str] = []
    for source_rel, dest_rel in REFERENCE_FILES:
        source = skill_dir / source_rel
        dest = context_root / dest_rel
        if not source.is_file():
            missing.append(source_rel)
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)
        copied.append(f"{ARTIFACT_ROOT}/{REFERENCE_CONTEXT_ROOT}/{dest_rel}".replace("\\", "/"))
    return {
        "reference_context_root": f"{ARTIFACT_ROOT}/{REFERENCE_CONTEXT_ROOT}",
        "copied_reference_files": copied,
        "missing_reference_files": missing,
        "reference_context_ready": not missing,
    }


def main() -> None:
    out_dir = lgwf_dir() / "prompt_acceptance"
    result = find_lgwf_client_assist()
    result["artifact_root"] = ARTIFACT_ROOT
    if not result["passed"]:
        write_json(out_dir / "environment_check.json", result)
        raise RuntimeError(result["reason"])
    result.update(prepare_reference_context(Path(result["skill_dir"]), out_dir))
    write_json(out_dir / "environment_check.json", result)
    if not result["reference_context_ready"]:
        raise RuntimeError("bundled lgwf-client-assist prompt reference context is incomplete")
    output_state({"environment_check": result})


if __name__ == "__main__":
    main()
