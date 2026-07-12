from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any


ARTIFACT_ROOT = ".lgwf/create_reference_context"
REFERENCE_CONTEXT_ROOT = "dsl-assist"
SCAFFOLD_CONTEXT_ROOT = "scaffold"
MODULAR_DEVELOPMENT_CONTEXT_ROOT = "workflow-modular-development"
MODULE_CONTRACT_CONTEXT_ROOT = "module-contract"
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
MODULAR_DEVELOPMENT_REFERENCE_FILES = (
    ("docs/LGWF_WF_MODULAR_DEVELOPMENT.md", "LGWF_WF_MODULAR_DEVELOPMENT.md"),
)
MODULE_CONTRACT_REFERENCE_FILES = (
    ("workflows/01-share/module-contract.md", "module-contract.md"),
)
STEP_DESIGN_DRAFT_DIR = Path("docs") / "steps"


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


def find_facade_root(start: Path, work_dir: Path | None = None) -> Path:
    roots = [start.resolve()]
    if work_dir is not None:
        roots.append(work_dir.resolve())

    seen: set[Path] = set()
    checked: list[Path] = []
    for root in roots:
        for parent in (root, *root.parents):
            if parent in seen:
                continue
            seen.add(parent)
            candidates = (
                parent,
                parent / "lgwf-wf-tools",
                parent / "skills" / "lgwf-wf-tools",
                parent / "workspace" / "skills" / "lgwf-wf-tools",
            )
            for candidate in candidates:
                marker = candidate / "docs" / "LGWF_WF_MODULAR_DEVELOPMENT.md"
                checked.append(marker)
                if marker.is_file():
                    return candidate
    checked_text = ", ".join(str(path) for path in checked)
    raise FileNotFoundError(f"未找到 facade 根目录，无法复制 workflow 模块化规范；已检查: {checked_text}")


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


def prepare_modular_development_context(facade_root: Path, out_dir: Path) -> dict[str, Any]:
    context_root = out_dir / MODULAR_DEVELOPMENT_CONTEXT_ROOT
    if context_root.exists():
        shutil.rmtree(context_root)
    copied: list[str] = []
    missing: list[str] = []
    for source_rel, dest_rel in MODULAR_DEVELOPMENT_REFERENCE_FILES:
        source = facade_root / source_rel
        dest = context_root / dest_rel
        if not source.is_file():
            missing.append(source_rel)
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)
        copied.append(f"{ARTIFACT_ROOT}/{MODULAR_DEVELOPMENT_CONTEXT_ROOT}/{dest_rel}".replace("\\", "/"))
    return {
        "modular_development_context_root": f"{ARTIFACT_ROOT}/{MODULAR_DEVELOPMENT_CONTEXT_ROOT}",
        "copied_modular_development_files": copied,
        "missing_modular_development_files": missing,
        "modular_development_context_ready": not missing,
        "source_facade_root": str(facade_root),
    }


def prepare_module_contract_context(facade_root: Path, out_dir: Path) -> dict[str, Any]:
    context_root = out_dir / MODULE_CONTRACT_CONTEXT_ROOT
    if context_root.exists():
        shutil.rmtree(context_root)
    copied: list[str] = []
    missing: list[str] = []
    for source_rel, dest_rel in MODULE_CONTRACT_REFERENCE_FILES:
        source = facade_root / source_rel
        dest = context_root / dest_rel
        if not source.is_file():
            missing.append(source_rel)
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)
        copied.append(f"{ARTIFACT_ROOT}/{MODULE_CONTRACT_CONTEXT_ROOT}/{dest_rel}".replace("\\", "/"))
    return {
        "module_contract_context_root": f"{ARTIFACT_ROOT}/{MODULE_CONTRACT_CONTEXT_ROOT}",
        "copied_module_contract_files": copied,
        "missing_module_contract_files": missing,
        "module_contract_context_ready": not missing,
    }


def reset_step_design_drafts(work_dir: Path) -> dict[str, Any]:
    draft_dir = work_dir / STEP_DESIGN_DRAFT_DIR
    removed = draft_dir.exists()
    if removed:
        shutil.rmtree(draft_dir)
    draft_dir.mkdir(parents=True, exist_ok=True)
    return {
        "step_design_draft_dir": STEP_DESIGN_DRAFT_DIR.as_posix(),
        "step_design_draft_dir_reset": True,
        "removed_previous_step_design_drafts": removed,
    }


def main() -> None:
    root = Path.cwd()
    out_dir = lgwf_dir(root) / "create_reference_context"
    skill_dir = find_bundled_client_dir(Path(__file__), root)
    workflow_root = find_workflow_root(Path(__file__))
    facade_root = find_facade_root(Path(__file__), root)
    draft_result = reset_step_design_drafts(root)
    result = prepare_reference_context(skill_dir, out_dir)
    scaffold_result = prepare_scaffold_context(workflow_root, out_dir)
    modular_development_result = prepare_modular_development_context(facade_root, out_dir)
    module_contract_result = prepare_module_contract_context(facade_root, out_dir)
    result.update(draft_result)
    result.update(scaffold_result)
    result.update(modular_development_result)
    result.update(module_contract_result)
    metadata = json.dumps(result, ensure_ascii=False, indent=2)
    (out_dir / "dsl_reference_context.json").write_text(metadata, encoding="utf-8")
    dsl_metadata = out_dir / REFERENCE_CONTEXT_ROOT / "dsl_reference_context.json"
    dsl_metadata.parent.mkdir(parents=True, exist_ok=True)
    dsl_metadata.write_text(metadata, encoding="utf-8")
    if not result["reference_context_ready"]:
        raise RuntimeError("bundled lgwf-client-assist dsl reference context is incomplete")
    if not result["scaffold_context_ready"]:
        raise RuntimeError("wf-create scaffold reference context is incomplete")
    if not result["modular_development_context_ready"]:
        raise RuntimeError("wf-create workflow modular development context is incomplete")
    if not result["module_contract_context_ready"]:
        raise RuntimeError("wf-create module contract context is incomplete")
    output_state(result)


if __name__ == "__main__":
    main()
