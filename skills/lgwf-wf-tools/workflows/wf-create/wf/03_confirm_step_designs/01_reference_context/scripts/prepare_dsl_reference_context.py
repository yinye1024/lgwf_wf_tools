from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any


ARTIFACT_ROOT = ".lgwf/create_reference_context"
REFERENCE_INDEX_FILE = "step-design-reference-index.md"
IMPLEMENTATION_REFERENCE_INDEX_FILE = "implementation-reference-index.md"
REFERENCE_CONTEXT_ROOT = "dsl-assist"
MODULAR_DEVELOPMENT_CONTEXT_ROOT = "workflow-modular-development"
MODULE_CONTRACT_CONTEXT_ROOT = "module-contract"
REFERENCE_FILES = (
    ("references/dsl-assist/guide.md", "guide.md"),
    ("references/dsl-assist/create-workflow.md", "create-workflow.md"),
    ("references/dsl-assist/workflow-audit-checklist.md", "workflow-audit-checklist.md"),
)
MODULAR_DEVELOPMENT_REFERENCE_FILES = (
    ("docs/LGWF_WF_MODULAR_DEVELOPMENT.md", "LGWF_WF_MODULAR_DEVELOPMENT.md"),
)
MODULE_CONTRACT_REFERENCE_FILES = (
    ("workflows/01-share/module-contract.md", "module-contract.md"),
)
REFERENCE_INDEX_SOURCE = Path("resources") / "step_design_reference_index.md"
IMPLEMENTATION_REFERENCE_INDEX_SOURCE = Path("resources") / "implementation_reference_index.md"


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


def prepare_reference_index(workflow_dir: Path, out_dir: Path) -> dict[str, Any]:
    source = workflow_dir / REFERENCE_INDEX_SOURCE
    dest = out_dir / REFERENCE_INDEX_FILE
    if not source.is_file():
        return {
            "reference_index_path": f"{ARTIFACT_ROOT}/{REFERENCE_INDEX_FILE}",
            "reference_index_ready": False,
            "missing_reference_index": str(REFERENCE_INDEX_SOURCE).replace("\\", "/"),
        }
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, dest)
    return {
        "reference_index_path": f"{ARTIFACT_ROOT}/{REFERENCE_INDEX_FILE}",
        "reference_index_ready": True,
        "copied_reference_index": f"{ARTIFACT_ROOT}/{REFERENCE_INDEX_FILE}",
    }


def prepare_implementation_reference_index(workflow_dir: Path, out_dir: Path) -> dict[str, Any]:
    source = workflow_dir / IMPLEMENTATION_REFERENCE_INDEX_SOURCE
    dest = out_dir / IMPLEMENTATION_REFERENCE_INDEX_FILE
    if not source.is_file():
        return {
            "implementation_reference_index_path": f"{ARTIFACT_ROOT}/{IMPLEMENTATION_REFERENCE_INDEX_FILE}",
            "implementation_reference_index_ready": False,
            "missing_implementation_reference_index": str(IMPLEMENTATION_REFERENCE_INDEX_SOURCE).replace("\\", "/"),
        }
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, dest)
    return {
        "implementation_reference_index_path": f"{ARTIFACT_ROOT}/{IMPLEMENTATION_REFERENCE_INDEX_FILE}",
        "implementation_reference_index_ready": True,
        "copied_implementation_reference_index": f"{ARTIFACT_ROOT}/{IMPLEMENTATION_REFERENCE_INDEX_FILE}",
    }


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


def remove_obsolete_scaffold_context(out_dir: Path) -> dict[str, Any]:
    context_root = out_dir / "scaffold"
    removed = context_root.exists()
    if removed:
        shutil.rmtree(context_root)
    return {
        "removed_obsolete_scaffold_context": removed,
    }


def remove_obsolete_dsl_reference_manifests(out_dir: Path) -> dict[str, Any]:
    obsolete_files = (
        out_dir / "dsl_reference_context.json",
        out_dir / REFERENCE_CONTEXT_ROOT / "dsl_reference_context.json",
    )
    removed: list[str] = []
    for path in obsolete_files:
        if path.exists():
            path.unlink()
            removed.append(str(path.relative_to(out_dir.parent)).replace("\\", "/"))
    return {
        "removed_obsolete_dsl_reference_manifests": removed,
    }


def main() -> None:
    root = Path.cwd()
    out_dir = lgwf_dir(root) / "create_reference_context"
    workflow_dir = Path(__file__).resolve().parents[1]
    skill_dir = find_bundled_client_dir(Path(__file__), root)
    facade_root = find_facade_root(Path(__file__), root)
    obsolete_scaffold_result = remove_obsolete_scaffold_context(out_dir)
    obsolete_dsl_manifest_result = remove_obsolete_dsl_reference_manifests(out_dir)
    result = prepare_reference_context(skill_dir, out_dir)
    index_result = prepare_reference_index(workflow_dir, out_dir)
    implementation_index_result = prepare_implementation_reference_index(workflow_dir, out_dir)
    modular_development_result = prepare_modular_development_context(facade_root, out_dir)
    module_contract_result = prepare_module_contract_context(facade_root, out_dir)
    result.update(obsolete_scaffold_result)
    result.update(obsolete_dsl_manifest_result)
    result.update(index_result)
    result.update(implementation_index_result)
    result.update(modular_development_result)
    result.update(module_contract_result)
    if not result["reference_context_ready"]:
        raise RuntimeError("bundled lgwf-client-assist dsl reference context is incomplete")
    if not result["reference_index_ready"]:
        raise RuntimeError("wf-create reference index is incomplete")
    if not result["implementation_reference_index_ready"]:
        raise RuntimeError("wf-create implementation reference index is incomplete")
    if not result["modular_development_context_ready"]:
        raise RuntimeError("wf-create workflow modular development context is incomplete")
    if not result["module_contract_context_ready"]:
        raise RuntimeError("wf-create module contract context is incomplete")
    output_state(result)


if __name__ == "__main__":
    main()
