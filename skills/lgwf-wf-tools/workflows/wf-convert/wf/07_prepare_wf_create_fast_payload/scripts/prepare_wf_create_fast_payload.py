from __future__ import annotations

import json
from pathlib import PurePosixPath
from typing import Any


REQUEST_SCALAR_FIELDS = ("target_dir", "target_file")
REQUEST_LIST_FIELDS = ("target_dirs", "target_files")
DOWNSTREAM_WORKFLOW_ID = "wf-create-fast"
DOWNSTREAM_WORKFLOW_LGWF = "workflows/wf-create-fast/wf/workflow.lgwf"


def normalize_package_path(raw_path: str, field_name: str) -> str:
    cleaned = raw_path.strip()
    candidate = PurePosixPath(cleaned.replace("\\", "/"))
    if not cleaned or cleaned == ".":
        raise ValueError(f"{field_name} 不能为空")
    if candidate.is_absolute():
        raise ValueError(f"{field_name} 禁止绝对路径")
    if ":" in cleaned:
        raise ValueError(f"{field_name} 禁止盘符路径")
    if any(part == ".." for part in candidate.parts):
        raise ValueError(f"{field_name} 禁止 `..`")
    if any(part == ".lgwf" for part in candidate.parts):
        raise ValueError(f"{field_name} 禁止写入 `.lgwf`")
    return candidate.as_posix().strip("/")


def as_string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            if isinstance(item, str) and item.strip():
                result.append(item.strip())
        return result
    return []


def dedupe_strings(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def normalize_creation_request(raw_request: Any) -> dict[str, Any]:
    if not isinstance(raw_request, dict):
        return {}
    request: dict[str, Any] = {}
    for field in REQUEST_SCALAR_FIELDS:
        values = as_string_list(raw_request.get(field))
        if values:
            request[field] = values[0]
    for field in REQUEST_LIST_FIELDS:
        values = dedupe_strings(as_string_list(raw_request.get(field)))
        if values:
            request[field] = values
    return request


def with_source_root_request(request: dict[str, Any], source_root: str) -> dict[str, Any]:
    cleaned_source_root = source_root.strip()
    if not cleaned_source_root:
        return request
    if not request.get("target_dir"):
        request["target_dir"] = cleaned_source_root
        return request
    if request.get("target_dir") == cleaned_source_root:
        return request
    target_dirs = as_string_list(request.get("target_dirs"))
    target_dirs.append(cleaned_source_root)
    request["target_dirs"] = dedupe_strings(target_dirs)
    return request


def build_payload(
    *,
    confirmed_input: dict[str, Any],
    package_profile: str = "internal_workflow_package",
) -> dict[str, Any]:
    target_package_root = normalize_package_path(
        str(confirmed_input.get("target_package_root", "")),
        "target_package_root",
    )
    workflow_name = str(confirmed_input.get("workflow_name", "")).strip() or "converted-workflow"
    raw_intent = str(confirmed_input.get("raw_intent", "")).strip()
    if not raw_intent:
        raw_intent = f"基于现有 prompt workflow 创建 LGWF workflow：{workflow_name}"
    payload = {
        "downstream_workflow_id": DOWNSTREAM_WORKFLOW_ID,
        "downstream_workflow_lgwf": DOWNSTREAM_WORKFLOW_LGWF,
        "workflow_name": workflow_name,
        "target_package_root": target_package_root,
        "source_root": str(confirmed_input.get("source_root", "")),
        "package_profile": package_profile,
        "raw_intent": raw_intent,
        "source_business_contract": confirmed_input.get("source_business_contract", {}),
        "conversion_mapping": confirmed_input.get("conversion_mapping", []),
        "prompt_workflow_context": {
            "stages": confirmed_input.get("stages", []),
            "prompt_contracts": confirmed_input.get("prompt_contracts", []),
            "prompt_execution_mechanics": confirmed_input.get("prompt_execution_mechanics", []),
            "presentation_constraints": confirmed_input.get("presentation_constraints", []),
            "discarded_prompt_techniques": confirmed_input.get("discarded_prompt_techniques", []),
            "parity_requirements": confirmed_input.get("parity_requirements", []),
            "assumptions": confirmed_input.get("assumptions", []),
            "out_of_scope": confirmed_input.get("out_of_scope", []),
        },
    }
    request = normalize_creation_request(confirmed_input.get("request"))
    if request:
        payload["request"] = request
    return payload


def build_wf_create_fast_input(payload: dict[str, Any]) -> dict[str, Any]:
    raw_intent = str(payload.get("raw_intent", "")).strip()
    child_input: dict[str, Any] = {"raw_intent": raw_intent}
    request = normalize_creation_request(payload.get("request"))
    request = with_source_root_request(request, str(payload.get("source_root", "")))
    if request:
        child_input["request"] = request
    for field in ("source_business_contract", "conversion_mapping", "prompt_workflow_context"):
        value = payload.get(field)
        if value:
            child_input[field] = value
    return child_input


def main() -> None:
    from pathlib import Path

    root = Path.cwd()
    lgwf_dir = root / ".lgwf"
    confirmed_input_path = lgwf_dir / "wf_create_fast_input.json"
    confirmed_input = json.loads(confirmed_input_path.read_text(encoding="utf-8-sig"))
    payload = build_payload(
        confirmed_input=confirmed_input,
        package_profile=str(confirmed_input.get("package_profile", "internal_workflow_package")),
    )
    wf_create_fast_input = build_wf_create_fast_input(payload)
    wf_create_fast_input_path = lgwf_dir / "wf_create_fast_input_for_wf_create_fast.json"
    wf_create_fast_input_path.write_text(
        json.dumps(wf_create_fast_input, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    output = {
        "downstream_workflow_id": DOWNSTREAM_WORKFLOW_ID,
        "prompt_convert_payload": payload,
        "wf_create_fast_payload": wf_create_fast_input,
    }
    output_path = lgwf_dir / "wf_create_fast_payload.json"
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"lgwf_wf_convert.wf_create_fast_payload": output}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
