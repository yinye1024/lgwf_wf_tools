from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any


ARTIFACT_ROOT = ".lgwf/create_reference_context"
REFERENCE_CONTEXT_ROOT = "dsl-assist"
SCAFFOLD_CONTEXT_ROOT = "scaffold"
REFERENCE_FILES = (
    ("references/dsl-assist/guide.md", "guide.md"),
    ("references/dsl-assist/create-workflow.md", "create-workflow.md"),
    ("references/dsl-assist/workflow-audit-checklist.md", "workflow-audit-checklist.md"),
)
SCAFFOLD_REFERENCE_FILES = (
    ("02_confirm_business_flow/resources/scaffold_template_spec.md", "scaffold_template_spec.md"),
    ("02_confirm_business_flow/resources/scaffold_result_contract.md", "scaffold_result_contract.md"),
    ("02_confirm_business_flow/resources/scaffold_package_template.json", "scaffold_package_template.json"),
)


def lgwf_dir(root: Path) -> Path:
    return root / ".lgwf"


def output_state(payload: dict[str, Any]) -> None:
    print(json.dumps({"lgwf_wf_create.dsl_reference_context": payload}, ensure_ascii=False, indent=2))


def find_bundled_client_dir(start: Path, work_dir: Path | None = None) -> Path:
    checked: list[Path] = []
    roots = [start.resolve()]
    if work_dir is not None:
        roots.append(work_dir.resolve())

    seen: set[Path] = set()
    parents: list[Path] = []
    for root in roots:
        for parent in (root, *root.parents):
            if parent in seen:
                continue
            seen.add(parent)
            parents.append(parent)

    for parent in parents:
        candidates = (
            parent / "vendor" / "lgwf-client-assist",
            parent / "workspace" / "vendor" / "lgwf-client-assist",
            parent / "lgwf-wf-tools" / "vendor" / "lgwf-client-assist",
            parent / "skills" / "lgwf-wf-tools" / "vendor" / "lgwf-client-assist",
        )
        for candidate in candidates:
            marker = candidate / "AGENTS.md"
            checked.append(marker)
            if marker.is_file():
                return candidate
    checked_text = ", ".join(str(path) for path in checked)
    raise FileNotFoundError(f"未找到 facade 内置 lgwf-client-assist vendor；已检查: {checked_text}")


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
        "source_skill_dir": str(skill_dir),
    }


def find_workflow_root(start: Path) -> Path:
    for parent in start.resolve().parents:
        if (parent / "workflow.lgwf").is_file() and (parent / "02_confirm_business_flow").is_dir():
            return parent
    raise FileNotFoundError("未找到 wf-create workflow root，无法复制 scaffold reference context")


def prepare_scaffold_context(workflow_root: Path, out_dir: Path) -> dict[str, Any]:
    context_root = out_dir / SCAFFOLD_CONTEXT_ROOT
    if context_root.exists():
        shutil.rmtree(context_root)
    copied: list[str] = []
    missing: list[str] = []
    for source_rel, dest_rel in SCAFFOLD_REFERENCE_FILES:
        source = workflow_root / source_rel
        dest = context_root / dest_rel
        if not source.is_file():
            missing.append(source_rel)
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)
        copied.append(f"{ARTIFACT_ROOT}/{SCAFFOLD_CONTEXT_ROOT}/{dest_rel}".replace("\\", "/"))
    return {
        "scaffold_context_root": f"{ARTIFACT_ROOT}/{SCAFFOLD_CONTEXT_ROOT}",
        "copied_scaffold_files": copied,
        "missing_scaffold_files": missing,
        "scaffold_context_ready": not missing,
        "source_workflow_root": str(workflow_root),
    }


def main() -> None:
    root = Path.cwd()
    out_dir = lgwf_dir(root) / "create_reference_context"
    skill_dir = find_bundled_client_dir(Path(__file__), root)
    workflow_root = find_workflow_root(Path(__file__))
    result = prepare_reference_context(skill_dir, out_dir)
    scaffold_result = prepare_scaffold_context(workflow_root, out_dir)
    result.update(scaffold_result)
    (out_dir / "dsl_reference_context.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if not result["reference_context_ready"]:
        raise RuntimeError("bundled lgwf-client-assist dsl reference context is incomplete")
    if not result["scaffold_context_ready"]:
        raise RuntimeError("wf-create scaffold reference context is incomplete")
    output_state(result)


if __name__ == "__main__":
    main()
