"""wf-create proposal 质量闸。

该模块在 REVIEW 前执行，和 `--auto-human` 无关。目标是先确认 Codex
proposal 是当前 run 的有效草案，再允许人工或自动审批继续。
"""

from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath
from typing import Any


WORKFLOW_ID_KEYS = ("workflow_id", "target_workflow_id", "workflow_name", "name")
TARGET_ROOT_KEYS = ("target_package_root", "package_root")
TARGET_HINT_KEYS = ("target_package_hint",)
CONTEXT_FILE_KEYS = ("target_file", "target_files", "creation_context_file", "creation_context_files")
ROOT_PACKAGE_FILES = {"SKILL.md", "AGENTS.md", "README.md", "entry_contract.json"}
PACKAGE_FILE_PATTERN = re.compile(r"[\w./:-]+\.(?:md|py|json|lgwf)")
PACKAGE_FILE_PREFIXES = {"scripts", "tests", "wf"}


def run_quality_gate(
    root: Path,
    *,
    stage: str,
    proposal_file: str,
    gate_file: str,
    input_files: list[str],
) -> dict[str, Any]:
    lgwf_dir = root / ".lgwf"
    proposal_path = lgwf_dir / proposal_file
    gate_path = lgwf_dir / gate_file
    result = evaluate_quality_gate(
        lgwf_dir,
        stage=stage,
        proposal_path=proposal_path,
        input_paths=[lgwf_dir / path for path in input_files],
    )
    write_json(gate_path, result)
    if not result["passed"]:
        failures = "; ".join(check["message"] for check in result["checks"] if not check["passed"])
        raise ValueError(f"{stage} proposal quality gate failed: {failures}")
    return result


def evaluate_quality_gate(
    lgwf_dir: Path,
    *,
    stage: str,
    proposal_path: Path,
    input_paths: list[Path],
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    proposal: dict[str, Any] = {}
    parse_error = ""

    if not proposal_path.is_file():
        checks.append(fail("proposal_exists", f"proposal 文件不存在: {relative_to_lgwf(lgwf_dir, proposal_path)}"))
    else:
        checks.append(pass_check("proposal_exists", "proposal 文件存在"))
        try:
            proposal = load_json_object(proposal_path)
            checks.append(pass_check("proposal_json_object", "proposal 是可解析的 JSON object"))
        except Exception as exc:
            parse_error = f"{type(exc).__name__}: {exc}"
            checks.append(fail("proposal_json_object", f"proposal JSON 不可解析: {parse_error}"))

    expected = expected_identity(input_paths)
    actual = identity_from_mapping(proposal)

    if proposal:
        if actual["workflow_id"]:
            checks.append(pass_check("workflow_id_present", "proposal 包含 workflow_id/workflow_name"))
        else:
            checks.append(fail("workflow_id_present", "proposal 缺少 workflow_id 或 workflow_name"))

        if actual["target_package_root"]:
            checks.append(pass_check("target_package_root_present", "proposal 包含 target_package_root"))
        else:
            checks.append(fail("target_package_root_present", "proposal 缺少 target_package_root"))

        if expected["workflow_id"] and actual["workflow_id"]:
            if normalize_identity(actual["workflow_id"]) == normalize_identity(expected["workflow_id"]):
                checks.append(pass_check("workflow_id_matches", "workflow id 与当前目标一致"))
            else:
                checks.append(
                    fail(
                        "workflow_id_matches",
                        f"workflow id 不一致: expected={expected['workflow_id']} actual={actual['workflow_id']}",
                    )
                )

        if expected["target_package_root"] and actual["target_package_root"]:
            if normalize_target_root(actual["target_package_root"]) == normalize_target_root(
                expected["target_package_root"]
            ):
                checks.append(pass_check("target_package_root_matches", "target_package_root 与当前目标一致"))
            else:
                checks.append(
                    fail(
                        "target_package_root_matches",
                        "target_package_root 不一致: "
                        f"expected={expected['target_package_root']} actual={actual['target_package_root']}",
                    )
                )

        stale_check = proposal_freshness_check(lgwf_dir, proposal_path, input_paths)
        if stale_check is not None:
            checks.append(stale_check)

        semantic_required_package_files: list[str] = []
        if stage == "create_requirements":
            semantic_required_package_files = semantic_package_files_from_inputs(input_paths, proposal)
            checks.extend(requirements_semantic_file_checks(proposal, semantic_required_package_files))
    else:
        semantic_required_package_files = []

    return {
        "stage": stage,
        "passed": all(check["passed"] for check in checks),
        "proposal_file": relative_to_lgwf(lgwf_dir, proposal_path),
        "expected_identity": expected,
        "actual_identity": actual,
        "reference_hints": reference_hints(input_paths),
        "semantic_required_package_files": semantic_required_package_files,
        "checks": checks,
        "parse_error": parse_error,
    }


def expected_identity(input_paths: list[Path]) -> dict[str, str]:
    candidates: list[dict[str, Any]] = []
    for path in input_paths:
        data = load_json_object_if_exists(path)
        if not data:
            continue
        candidates.extend(identity_candidates(data))
    return {
        "workflow_id": first_identity_value(candidates, WORKFLOW_ID_KEYS),
        "target_package_root": first_identity_value(candidates, TARGET_ROOT_KEYS),
    }


def reference_hints(input_paths: list[Path]) -> dict[str, str]:
    candidates: list[dict[str, Any]] = []
    for path in input_paths:
        data = load_json_object_if_exists(path)
        if data:
            candidates.extend(identity_candidates(data))
    return {
        "target_package_hint": first_identity_value(candidates, TARGET_HINT_KEYS),
    }


def identity_from_mapping(data: dict[str, Any]) -> dict[str, str]:
    candidates = identity_candidates(data)
    return {
        "workflow_id": first_identity_value(candidates, WORKFLOW_ID_KEYS),
        "target_package_root": first_identity_value(candidates, TARGET_ROOT_KEYS),
    }


def identity_candidates(data: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    if not isinstance(data, dict):
        return candidates
    candidates.append(data)
    for key in ("target_identity", "identity", "confirmed", "scaffold_plan", "request"):
        value = data.get(key)
        if isinstance(value, dict):
            candidates.append(value)
            nested_request = value.get("request")
            if isinstance(nested_request, dict):
                candidates.append(nested_request)
    return candidates


def first_identity_value(candidates: list[dict[str, Any]], keys: tuple[str, ...]) -> str:
    for candidate in candidates:
        for key in keys:
            value = candidate.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return ""


def proposal_freshness_check(lgwf_dir: Path, proposal_path: Path, input_paths: list[Path]) -> dict[str, Any] | None:
    existing_inputs = [path for path in input_paths if path.is_file()]
    if not existing_inputs:
        return None
    proposal_mtime = proposal_path.stat().st_mtime
    newest_input = max(existing_inputs, key=lambda path: path.stat().st_mtime)
    if proposal_mtime + 0.001 >= newest_input.stat().st_mtime:
        return pass_check("proposal_fresh_enough", "proposal 不早于当前上游输入")
    return fail(
        "proposal_fresh_enough",
        "proposal 早于当前上游输入，可能读取了旧草案: "
        f"proposal={relative_to_lgwf(lgwf_dir, proposal_path)} input={relative_to_lgwf(lgwf_dir, newest_input)}",
    )


def requirements_semantic_file_checks(proposal: dict[str, Any], required_files: list[str]) -> list[dict[str, Any]]:
    if not required_files:
        return []
    proposal_text = flatten_text(proposal).replace("\\", "/")
    checks: list[dict[str, Any]] = []
    for rel_path in required_files:
        checks.append(
            check(
                f"semantic_package_file_preserved_{safe_check_suffix(rel_path)}",
                rel_path in proposal_text,
                "需求 proposal 必须保留参考资料中明确的目标 package 源文件 "
                f"`{rel_path}`，不能泛化为直接脚本入口、最小测试或宽泛模块说明。",
            )
        )
    return checks


def semantic_package_files_from_inputs(input_paths: list[Path], proposal: dict[str, Any]) -> list[str]:
    input_payloads: list[tuple[Path, dict[str, Any]]] = []
    for path in input_paths:
        data = load_json_object_if_exists(path)
        if data:
            input_payloads.append((path, data))
    package_roots = semantic_package_roots([payload for _, payload in input_payloads], proposal)
    files: list[str] = []
    for input_path, payload in input_payloads:
        for reference_path in context_reference_paths(payload):
            path = resolve_context_path(reference_path, input_path.parent.parent)
            if not path.is_file():
                continue
            text = read_text_reference(path)
            files.extend(extract_package_files_from_text(text, package_roots))
    return unique(files)


def semantic_package_roots(input_payloads: list[dict[str, Any]], proposal: dict[str, Any]) -> list[str]:
    candidates: list[dict[str, Any]] = []
    for payload in input_payloads:
        candidates.extend(identity_candidates(payload))
    candidates.extend(identity_candidates(proposal))
    roots = [candidate.get(key) for candidate in candidates for key in TARGET_ROOT_KEYS]
    normalized: list[str] = []
    for value in roots:
        if not isinstance(value, str) or not value.strip():
            continue
        root = value.strip().replace("\\", "/").strip("/")
        if root:
            normalized.append(root)
            name = PurePosixPath(root).name
            if name and name != root:
                normalized.append(name)
    return unique(normalized)


def context_reference_paths(value: Any) -> list[str]:
    paths: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in CONTEXT_FILE_KEYS:
                paths.extend(as_string_list(child))
            if isinstance(child, (dict, list)):
                paths.extend(context_reference_paths(child))
    elif isinstance(value, list):
        for child in value:
            paths.extend(context_reference_paths(child))
    return unique(paths)


def as_string_list(value: Any) -> list[str]:
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    if isinstance(value, list):
        return [item.strip() for item in value if isinstance(item, str) and item.strip()]
    return []


def resolve_context_path(raw_path: str, base_dir: Path) -> Path:
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return candidate
    return base_dir / candidate


def read_text_reference(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def extract_package_files_from_text(text: str, package_roots: list[str]) -> list[str]:
    files: list[str] = []
    normalized_text = text.replace("\\", "/")
    for match in PACKAGE_FILE_PATTERN.findall(normalized_text):
        path = normalize_package_file_candidate(match, package_roots)
        if path:
            files.append(path)
    return unique(files)


def normalize_package_file_candidate(raw_path: str, package_roots: list[str]) -> str:
    cleaned = raw_path.strip("`'\"“”‘’，,。；;：:（）()[]{}<>")
    if not cleaned:
        return ""
    cleaned = cleaned.replace("\\", "/")
    for package_root in package_roots:
        root = package_root.strip("/")
        if not root:
            continue
        marker = f"/{root}/"
        if marker in cleaned:
            cleaned = cleaned.split(marker, 1)[1]
            break
        if cleaned.startswith(f"{root}/"):
            cleaned = cleaned[len(root) + 1 :]
            break
    cleaned = cleaned.lstrip("./")
    try:
        path = normalize_target_root(cleaned)
    except Exception:
        return ""
    parts = PurePosixPath(path).parts
    if not parts or parts[0] in {".lgwf", "ws"}:
        return ""
    if path in ROOT_PACKAGE_FILES or parts[0] in PACKAGE_FILE_PREFIXES:
        return path
    return ""


def flatten_text(value: Any) -> str:
    if isinstance(value, dict):
        return "\n".join(flatten_text(child) for child in value.values())
    if isinstance(value, list):
        return "\n".join(flatten_text(child) for child in value)
    return str(value) if value is not None else ""


def unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def safe_check_suffix(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_")


def check(name: str, condition: bool, message: str) -> dict[str, Any]:
    return pass_check(name, message) if condition else fail(name, message)


def load_json_object(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise TypeError(f"{path.as_posix()} 必须是 JSON object")
    return data


def load_json_object_if_exists(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return load_json_object(path)
    except Exception:
        return {}


def normalize_identity(value: str) -> str:
    return value.strip()


def normalize_target_root(value: str) -> str:
    candidate = PurePosixPath(value.strip().replace("\\", "/"))
    return candidate.as_posix().strip("/")


def relative_to_lgwf(lgwf_dir: Path, path: Path) -> str:
    try:
        return ".lgwf/" + path.relative_to(lgwf_dir).as_posix()
    except ValueError:
        return path.as_posix()


def pass_check(name: str, message: str) -> dict[str, Any]:
    return {"name": name, "passed": True, "message": message}


def fail(name: str, message: str) -> dict[str, Any]:
    return {"name": name, "passed": False, "message": message}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
