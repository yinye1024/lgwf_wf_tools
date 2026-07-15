"""在 FOREACH child 中物化当前 implementation unit 的 staging 输出上下文。"""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path, PurePosixPath
from typing import Any

STAGING_ROOT = Path(".lgwf") / "implementation_stage"
SENSITIVE_UNIT_FIELDS = {"target_package_abs", "workspace_root"}
SCHEMA_RESOURCE = Path(__file__).resolve().parents[1] / "resources" / "codex_output_schemas.json"
LGWF_IDENTIFIER_PATTERN = re.compile(r"[^A-Za-z0-9_]+")
WORKSPACE_ARTIFACT_PATTERN = re.compile(r"(?:ws/)?(?:\.lgwf|reports)/[\w./-]+\.[A-Za-z0-9]+")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_payload() -> dict[str, Any]:
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    data = json.loads(raw)
    return data if isinstance(data, dict) else {}


def load_schema_registry() -> dict[str, Any]:
    if not SCHEMA_RESOURCE.is_file():
        return {}
    data = json.loads(SCHEMA_RESOURCE.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def safe_unit_id(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip()).strip("._-")
    return cleaned or "unit"


def safe_lgwf_identifier(value: str, fallback: str) -> str:
    cleaned = LGWF_IDENTIFIER_PATTERN.sub("_", value.strip()).strip("_")
    if not cleaned:
        cleaned = fallback
    if not re.match(r"^[A-Za-z_]", cleaned):
        cleaned = f"stage_{cleaned}"
    return cleaned


def is_stage_artifact_contract_file(output_file: str) -> bool:
    parts = PurePosixPath(output_file).parts
    return len(parts) == 3 and parts[0] == "wf" and parts[2] == "artifact_contracts.json"


def normalize_workspace_artifact(raw_path: str) -> str:
    normalized = raw_path.strip().strip("`'\"“”‘’，,。；;：:（）()[]{}<>").replace("\\", "/")
    if normalized.startswith("ws/"):
        normalized = normalized.removeprefix("ws/")
    return normalized


def workspace_artifacts_from_values(values: Any) -> list[str]:
    artifacts: list[str] = []
    for value in string_list(values):
        for match in WORKSPACE_ARTIFACT_PATTERN.findall(value.replace("\\", "/")):
            artifact = normalize_workspace_artifact(match)
            if artifact.startswith(".lgwf/") or artifact.startswith("reports/"):
                artifacts.append(artifact)
    return unique(artifacts)


def stage_dir_from_design_item(item: dict[str, Any]) -> str:
    for field in ("target_files", "outputs"):
        for raw_path in string_list(item.get(field)):
            parts = PurePosixPath(raw_path.replace("\\", "/")).parts
            if len(parts) >= 3 and parts[0] == "wf" and parts[1] not in {"shared", "docs"}:
                return parts[1]
    return ""


def stage_boundary_hints(step_designs: list[Any], file_designs: list[Any]) -> list[dict[str, Any]]:
    refs = root_workflow_child_refs(step_designs, file_designs)
    by_stage_dir: dict[str, dict[str, Any]] = {
        item["stage_dir"]: {
            **item,
            "stage_id": "",
            "contract_reads": [],
            "contract_writes": [],
        }
        for item in refs
    }
    ordered_stage_dirs = [item["stage_dir"] for item in refs]
    for item in step_designs:
        if not isinstance(item, dict):
            continue
        stage_dir = stage_dir_from_design_item(item)
        if not stage_dir:
            continue
        if stage_dir not in by_stage_dir:
            by_stage_dir[stage_dir] = {
                "stage_dir": stage_dir,
                "step_id": safe_lgwf_identifier(stage_dir, "stage"),
                "workflow_ref_from_wf_root": f"{stage_dir}/workflow.lgwf",
                "stage_id": "",
                "contract_reads": [],
                "contract_writes": [],
            }
            ordered_stage_dirs.append(stage_dir)
        entry = by_stage_dir[stage_dir]
        entry["stage_id"] = str(item.get("stage_id") or item.get("stage") or entry.get("stage_id") or "").strip()
        entry["contract_reads"] = unique(
            [
                *entry.get("contract_reads", []),
                *workspace_artifacts_from_values(item.get("inputs")),
            ]
        )
        entry["contract_writes"] = unique(
            [
                *entry.get("contract_writes", []),
                *workspace_artifacts_from_values(item.get("outputs")),
                *workspace_artifacts_from_values(item.get("runtime_artifacts")),
            ]
        )
    return [by_stage_dir[stage_dir] for stage_dir in ordered_stage_dirs if stage_dir in by_stage_dir]


def artifact_contract_guidance(unit: dict[str, Any], output_files: list[str]) -> dict[str, Any]:
    artifact_outputs = [path for path in output_files if path == "wf/artifact_contracts.json" or is_stage_artifact_contract_file(path)]
    if not artifact_outputs:
        return {"required": False, "reason": "当前 unit 不生成 artifact_contracts.json"}

    boundaries = stage_boundary_hints(
        as_list(unit.get("step_designs", [])),
        as_list(unit.get("file_designs", [])),
    )
    all_reads = {artifact for item in boundaries for artifact in item.get("contract_reads", [])}
    all_writes = unique([artifact for item in boundaries for artifact in item.get("contract_writes", [])])
    root_final_outputs = [artifact for artifact in all_writes if artifact not in all_reads or artifact.startswith("reports/")]

    stage_by_dir = {str(item.get("stage_dir", "")): item for item in boundaries}
    stage_guidance: dict[str, dict[str, Any]] = {}
    for output_file in artifact_outputs:
        if not is_stage_artifact_contract_file(output_file):
            continue
        stage_dir = PurePosixPath(output_file).parts[1]
        boundary = stage_by_dir.get(stage_dir, {})
        stage_guidance[output_file] = {
            "stage_dir": stage_dir,
            "stage_id": boundary.get("stage_id", ""),
            "bootstrap_inputs": boundary.get("contract_reads", []),
            "final_outputs": boundary.get("contract_writes", []),
            "audit_scope": f"lgwf.py audit wf/{stage_dir}/workflow.lgwf",
        }

    return {
        "required": True,
        "artifact_outputs": artifact_outputs,
        "root_workflow_step_boundaries": boundaries,
        "root_artifact_contract": {
            "bootstrap_inputs": [
                artifact
                for artifact in unique([artifact for item in boundaries for artifact in item.get("contract_reads", [])])
                if artifact not in set(all_writes)
            ],
            "handoff_artifacts": [artifact for artifact in all_writes if artifact in all_reads],
            "final_outputs": root_final_outputs,
            "audit_scope": "lgwf.py audit wf/workflow.lgwf",
        },
        "stage_artifact_contracts": stage_guidance,
        "workspace_path_convention": [
            "artifact_contracts.json 中使用 workflow package root 视角的 workspace path。",
            "从 step_designs 中提取到的 `ws/.lgwf/...` 统一写成 `.lgwf/...`。",
            "报告类 workspace 文件统一写成 `reports/...`。",
        ],
    }


def root_workflow_child_refs(step_designs: list[Any], file_designs: list[Any]) -> list[dict[str, str]]:
    stage_dirs: list[str] = []
    for collection in (step_designs, file_designs):
        if not isinstance(collection, list):
            continue
        for item in collection:
            if not isinstance(item, dict):
                continue
            paths: list[Any] = []
            for field in ("target_files", "outputs"):
                value = item.get(field)
                if isinstance(value, list):
                    paths.extend(value)
            raw_path = item.get("path")
            if isinstance(raw_path, str):
                paths.append(raw_path)
            for raw in paths:
                if not isinstance(raw, str):
                    continue
                normalized = raw.strip().replace("\\", "/")
                parts = PurePosixPath(normalized).parts
                if len(parts) >= 3 and parts[0] == "wf" and parts[1] not in {"shared", "docs"}:
                    if parts[-1] == "workflow.lgwf":
                        stage_dirs.append(parts[1])
    refs: list[dict[str, str]] = []
    for stage_dir in unique(stage_dirs):
        refs.append(
            {
                "stage_dir": stage_dir,
                "step_id": safe_lgwf_identifier(stage_dir, "stage"),
                "workflow_ref_from_wf_root": f"{stage_dir}/workflow.lgwf",
            }
        )
    return refs


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def normalize_output_path(raw_path: str, *, allow_root: bool = False) -> str:
    cleaned = raw_path.strip().replace("\\", "/")
    path = PurePosixPath(cleaned)
    if not cleaned or path.is_absolute() or ":" in cleaned:
        raise ValueError(f"非法 unit 输出路径: {raw_path}")
    if any(part in {"..", ".lgwf"} for part in path.parts):
        raise ValueError(f"非法 unit 输出路径: {raw_path}")
    normalized = path.as_posix().strip("/")
    if normalized == "." and not allow_root:
        raise ValueError(f"非法 unit 输出文件路径: {raw_path}")
    return normalized


def normalize_output_files(unit: dict[str, Any]) -> list[str]:
    raw_files = (
        string_list(unit.get("output_files", []))
        or string_list(unit.get("package_relative_files", []))
        or string_list(unit.get("planned_files", []))
    )
    return unique([normalize_output_path(path) for path in raw_files])


def normalize_output_dirs(unit: dict[str, Any], output_files: list[str]) -> list[str]:
    raw_dirs = (
        string_list(unit.get("output_dirs", []))
        or string_list(unit.get("package_relative_dirs", []))
        or string_list(unit.get("planned_dirs", []))
    )
    dirs = [normalize_output_path(path, allow_root=True) for path in raw_dirs]
    for output_file in output_files:
        parent = PurePosixPath(output_file).parent.as_posix()
        dirs.append("." if parent == "." else parent)
    return unique(dirs)


def unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def ensure_within(path: Path, parent: Path, label: str) -> Path:
    resolved = path.resolve()
    resolved_parent = parent.resolve()
    if resolved != resolved_parent and not resolved.is_relative_to(resolved_parent):
        raise ValueError(f"{label} 越过允许目录: {resolved} 不在 {resolved_parent} 下")
    return resolved


def workspace_rel(path: Path) -> str:
    return path.as_posix()


def sanitized_unit(unit: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in unit.items() if key not in SENSITIVE_UNIT_FIELDS}


def prepare_staging(
    root: Path,
    unit_output_dir: str,
    output_dirs: list[str],
    output_files: list[str],
    target_package_abs: str,
) -> tuple[list[str], list[str]]:
    staging_root_abs = (root / STAGING_ROOT).resolve()
    unit_output_abs = ensure_within(root / unit_output_dir, staging_root_abs, "unit_output_dir")
    if unit_output_abs.exists():
        shutil.rmtree(unit_output_abs)
    unit_output_abs.mkdir(parents=True, exist_ok=True)

    workspace_output_dirs: list[str] = []
    for output_dir in output_dirs:
        rel_dir = "" if output_dir == "." else output_dir
        output_path = ensure_within(unit_output_abs / rel_dir, unit_output_abs, "workspace_output_dir")
        output_path.mkdir(parents=True, exist_ok=True)
        workspace_output_dirs.append(workspace_rel(Path(unit_output_dir) / rel_dir) if rel_dir else unit_output_dir)

    target_abs = Path(target_package_abs).resolve() if target_package_abs else None
    workspace_output_files: list[str] = []
    for output_file in output_files:
        output_path = ensure_within(unit_output_abs / output_file, unit_output_abs, "workspace_output_file")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        workspace_output_files.append(workspace_rel(Path(unit_output_dir) / output_file))
        if target_abs is None:
            continue
        source_path = ensure_within(target_abs / output_file, target_abs, "target_source_file")
        if source_path.is_file():
            shutil.copy2(source_path, output_path)
    return unique(workspace_output_dirs), workspace_output_files


def output_file_schemas(output_files: list[str], schema_registry: dict[str, Any]) -> dict[str, Any]:
    raw_schemas = schema_registry.get("target_package_output_file_schemas", {})
    if not isinstance(raw_schemas, dict):
        return {}
    schemas: dict[str, Any] = {}
    wildcard_stage_artifact_schema = raw_schemas.get("wf/*/artifact_contracts.json")
    for output_file in output_files:
        schema = raw_schemas.get(output_file)
        if not isinstance(schema, dict) and is_stage_artifact_contract_file(output_file):
            schema = wildcard_stage_artifact_schema
        if isinstance(schema, dict):
            schemas[output_file] = schema
    return schemas


def codex_output_schema(schema_registry: dict[str, Any]) -> dict[str, Any]:
    raw_schemas = schema_registry.get("codex_output_json_schemas", {})
    schema = raw_schemas.get(".lgwf/current_implementation_unit_result.json", {}) if isinstance(raw_schemas, dict) else {}
    return schema if isinstance(schema, dict) else {}


def build_current_implementation_unit_context(root: Path, unit: dict[str, Any]) -> dict[str, Any]:
    unit_id = str(unit.get("unit_id", "")).strip() or "unit"
    output_files = normalize_output_files(unit)
    output_dirs = normalize_output_dirs(unit, output_files)
    target_package_abs = str(unit.get("target_package_abs", "")).strip()
    safe_id = safe_unit_id(unit_id)
    unit_output_dir = workspace_rel(STAGING_ROOT / safe_id)
    workspace_output_dirs, workspace_output_files = prepare_staging(
        root,
        unit_output_dir,
        output_dirs,
        output_files,
        target_package_abs,
    )
    schema_registry = load_schema_registry()
    safe_unit = sanitized_unit(unit)
    context = {
        "current_implementation_unit": safe_unit,
        "unit_id": unit_id,
        "unit_type": safe_unit.get("unit_type", ""),
        "objective": safe_unit.get("objective", ""),
        "stage_id": safe_unit.get("stage_id", ""),
        "stage_dir": safe_unit.get("stage_dir", ""),
        "workflow_ref": safe_unit.get("workflow_ref", ""),
        "planned_files": safe_unit.get("planned_files", output_files),
        "planned_dirs": safe_unit.get("planned_dirs", output_dirs),
        "step_designs": safe_unit.get("step_designs", []),
        "file_designs": safe_unit.get("file_designs", []),
        "directory_designs": safe_unit.get("directory_designs", []),
        "unit_output_dir": unit_output_dir,
        "output_files": output_files,
        "output_dirs": output_dirs,
        "workspace_output_files": workspace_output_files,
        "workspace_output_dirs": workspace_output_dirs,
        "codex_output_json_schema": codex_output_schema(schema_registry),
        "target_output_file_schemas": output_file_schemas(output_files, schema_registry),
        "artifact_contract_guidance": artifact_contract_guidance(safe_unit, output_files),
        "instructions": [
            "只处理 current_implementation_unit 指定的输出文件。",
            "只能写入 unit_output_dir 下的 workspace_output_files，保持 output_files 的 package 相对路径结构。",
            "不要直接写最终目标 package；发布脚本会把 unit_output_dir 中的文件复制到目标 package。",
            "生成 JSON 输出文件时只能使用 target_output_file_schemas 中随当前 context 提供的 schema；缺少 schema 时记录 blocked_reason，不要递归搜索 .lgwf 或读取宿主仓库样例。",
            "file_designs 中 content_mode=exact 的文件必须按 exact_content 生成；content_mode=contract 的文件必须按 script_contract、markdown_contract、json_contract 或 test_contract 实现。",
            "不得保留 LGWF_PLACEHOLDER 或 _lgwf_placeholder 等占位内容。",
            "生成或修改 workflow.lgwf、agents/*.md 等声明式完整文本时只能使用 file_designs[].exact_content；缺失 exact_content 时记录 blocked_reason，不要自行发明 DSL 或 prompt。",
            "生成 artifact_contracts.json 时必须使用 artifact_contract_guidance 中的 root_workflow_step_boundaries、root_artifact_contract 或 stage_artifact_contracts；不要把跨阶段 handoff 留给后续 repair 猜测。",
            "本准备脚本不生成、不筛选、不摘录 LGWF DSL schema 或模板；实现阶段只能消费步骤设计中已确认的 exact_content 和结构化合同。",
            "如果目标实现需要扩大到其他 unit，输出 blocked_reason，不要擅自修改。",
        ],
    }
    write_json(root / ".lgwf" / "current_implementation_unit_context.json", context)
    return context


def main() -> None:
    context = build_current_implementation_unit_context(Path.cwd(), read_payload())
    print(
        json.dumps(
            {
                "lgwf_wf_create.current_implementation_unit_context": context,
                "lgwf_wf_create.current_implementation_unit_output_files": context["output_files"],
                "lgwf_wf_create.current_implementation_unit_output_dirs": context["output_dirs"],
                "lgwf_wf_create.current_implementation_unit_output_dir": context["unit_output_dir"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
