"""wf-maintenance-gate 共享 helper。"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


RISK_ORDER = {"low": 1, "medium": 2, "high": 3}

IMPACT_RULES = [
    {
        "rule_id": "registry_json",
        "pattern": "skills/lgwf-wf-tools/registry.json",
        "category": "facade_entry",
        "priority": 100,
        "risk": "high",
        "impacted_workflow_strategy": "all_workflows",
        "recommended_checks": ["doctor_basic", "deep_doctor"],
    },
    {
        "rule_id": "facade_docs",
        "pattern": "skills/lgwf-wf-tools/{SKILL,AGENTS,README}.md",
        "category": "facade_entry",
        "priority": 90,
        "risk": "medium",
        "impacted_workflow_strategy": "all_workflows",
        "recommended_checks": ["doctor_basic"],
    },
    {
        "rule_id": "shared_contract",
        "pattern": "skills/lgwf-wf-tools/workflows/01-share/**",
        "category": "shared_contract",
        "priority": 100,
        "risk": "high",
        "impacted_workflow_strategy": "all_workflows",
        "recommended_checks": ["doctor_basic", "deep_doctor", "workflow_tests"],
    },
    {
        "rule_id": "modular_development_doc",
        "pattern": "skills/lgwf-wf-tools/docs/LGWF_WF_MODULAR_DEVELOPMENT.md",
        "category": "shared_contract",
        "priority": 95,
        "risk": "high",
        "impacted_workflow_strategy": "all_workflows",
        "recommended_checks": ["doctor_basic", "deep_doctor"],
    },
    {
        "rule_id": "workflow_entry_contract",
        "pattern": "skills/lgwf-wf-tools/workflows/<id>/entry_contract.json",
        "category": "workflow_source",
        "priority": 95,
        "risk": "high",
        "impacted_workflow_strategy": "from_registry_path",
        "recommended_checks": ["doctor_basic", "deep_doctor", "workflow_tests"],
    },
    {
        "rule_id": "workflow_source",
        "pattern": "skills/lgwf-wf-tools/workflows/<id>/wf/**",
        "category": "workflow_source",
        "priority": 90,
        "risk": "high",
        "impacted_workflow_strategy": "from_registry_path",
        "recommended_checks": ["doctor_basic", "workflow_tests"],
    },
    {
        "rule_id": "workflow_agents",
        "pattern": "skills/lgwf-wf-tools/workflows/<id>/AGENTS.md",
        "category": "workflow_source",
        "priority": 85,
        "risk": "medium",
        "impacted_workflow_strategy": "from_registry_path",
        "recommended_checks": ["doctor_basic", "workflow_tests"],
    },
    {
        "rule_id": "workflow_tests",
        "pattern": "skills/lgwf-wf-tools/workflows/<id>/tests/**",
        "category": "workflow_tests",
        "priority": 70,
        "risk": "medium",
        "impacted_workflow_strategy": "from_registry_path",
        "recommended_checks": ["workflow_tests"],
    },
    {
        "rule_id": "self_improve",
        "pattern": "skills/lgwf-wf-tools/workflows/self-improve/**",
        "category": "self_improve",
        "priority": 90,
        "risk": "high",
        "impacted_workflow_strategy": "self_improve",
        "recommended_checks": ["self_improve_health", "pre_release"],
    },
    {
        "rule_id": "vendor",
        "pattern": "skills/lgwf-wf-tools/vendor/lgwf-client-assist/**",
        "category": "vendor",
        "priority": 100,
        "risk": "high",
        "impacted_workflow_strategy": "all_workflows",
        "recommended_checks": ["doctor_basic", "deep_doctor", "workflow_tests"],
    },
    {
        "rule_id": "packaging",
        "pattern": "skills/lgwf-wf-tools/scripts/{package_lgwf_wf_tools_zip.py,package_lgwf_skill.py}",
        "category": "packaging",
        "priority": 90,
        "risk": "high",
        "impacted_workflow_strategy": "none",
        "recommended_checks": ["doctor_basic", "package_smoke"],
    },
    {
        "rule_id": "skill_packaging",
        "pattern": "skills/lgwf-wf-tools/workflows/skill-packaging/**",
        "category": "packaging",
        "priority": 90,
        "risk": "high",
        "impacted_workflow_strategy": "none",
        "recommended_checks": ["doctor_basic", "package_smoke"],
    },
    {
        "rule_id": "scripts",
        "pattern": "skills/lgwf-wf-tools/scripts/**",
        "category": "scripts",
        "priority": 75,
        "risk": "medium",
        "impacted_workflow_strategy": "none",
        "recommended_checks": ["doctor_basic"],
    },
    {
        "rule_id": "docs_only",
        "pattern": "*.md",
        "category": "docs_only",
        "priority": 10,
        "risk": "low",
        "impacted_workflow_strategy": "none",
        "recommended_checks": [],
    },
]

COMMAND_TEMPLATES = {
    "doctor_basic": {
        "check_id": "doctor_basic",
        "command": ["python", "skills/lgwf-wf-tools/scripts/doctor_lgwf_wf_tools.py"],
        "cwd": ".",
        "timeout_seconds": 120,
        "write_effects": [],
        "requires_allow": None,
        "short_circuit": True,
        "failure_type": "entry_contract",
    },
    "deep_doctor": {
        "check_id": "deep_doctor",
        "command": ["python", "skills/lgwf-wf-tools/scripts/doctor_lgwf_wf_tools.py", "--deep"],
        "cwd": ".",
        "timeout_seconds": 300,
        "write_effects": [".local/doctor/"],
        "requires_allow": "allow_deep_doctor",
        "short_circuit": False,
        "failure_type": "entry_contract",
    },
    "self_improve_health": {
        "check_id": "self_improve_health",
        "command": ["python", "skills/lgwf-wf-tools/workflows/self-improve/scripts/self_improve.py", "workflow-health"],
        "cwd": ".",
        "timeout_seconds": 300,
        "write_effects": [".local/self-improve/"],
        "requires_allow": None,
        "short_circuit": False,
        "failure_type": "self_improve_health",
    },
    "pre_release": {
        "check_id": "pre_release",
        "command": ["python", "skills/lgwf-wf-tools/workflows/self-improve/scripts/self_improve.py", "pre-release", "--source", "wf-maintenance-gate"],
        "cwd": ".",
        "timeout_seconds": 600,
        "write_effects": [".local/self-improve/"],
        "requires_allow": "allow_pre_release",
        "short_circuit": False,
        "failure_type": "pre_release",
    },
    "package_smoke": {
        "check_id": "package_smoke",
        "command": ["python", "skills/lgwf-wf-tools/scripts/package_lgwf_wf_tools_zip.py"],
        "cwd": ".",
        "timeout_seconds": 600,
        "write_effects": ["skills/lgwf-wf-tools/output/"],
        "requires_allow": "allow_package_smoke",
        "short_circuit": False,
        "failure_type": "packaging",
    },
}

FAILURE_ROUTE_RULES = {
    "dsl_audit": {"route": "wf-audit-fix", "reason": "DSL 结构或运行拓扑失败"},
    "workflow_compile": {"route": "wf-audit-fix", "reason": "workflow 编译失败"},
    "prompt_contract": {"route": "wf-prompt-fix", "reason": "prompt 输入输出契约不满足"},
    "prompt_quality": {"route": "wf-prompt-upgrade", "reason": "prompt 质量需要升级"},
    "entry_contract": {"route": "wf-fix", "reason": "入口或 facade 健康检查失败"},
    "artifact_contract": {"route": "wf-fix", "reason": "artifact 契约不一致"},
    "registry": {"route": "wf-fix", "reason": "registry 或映射关系异常"},
    "missing_tests": {"route": "e2e-test-generator", "reason": "缺少可执行测试"},
    "test_failure": {"route": "wf-fix", "reason": "测试失败，需要修复实现或测试"},
    "self_improve_health": {"route": "self-improve", "reason": "self-improve 健康检查失败"},
    "pre_release": {"route": "self-improve", "reason": "pre-release 检查失败"},
    "packaging": {"route": "skill-packaging", "reason": "打包或 zip smoke 失败"},
    "zip_conflict": {"route": "needs_review", "reason": "输出 zip 冲突需要人工确认"},
    "timeout": {"route": "needs_review", "reason": "命令超时，需要人工判断"},
    "command_contract": {"route": "needs_review", "reason": "命令或 cwd 契约异常"},
}


def find_workspace_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists():
            return candidate
    for candidate in [current, *current.parents]:
        if (candidate / "skills" / "lgwf-wf-tools" / "registry.json").is_file():
            return candidate
    raise RuntimeError(f"无法从 {start} 推导 workspace root")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise TypeError(f"{path.as_posix()} 必须是 JSON object")
    return payload


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_stdin_object() -> dict[str, Any]:
    raw = sys.stdin.read().strip()
    if raw:
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise TypeError("stdin payload 必须是 JSON object")
        return payload
    fallback = Path.cwd() / ".lgwf" / "input_state.json"
    if fallback.is_file():
        payload = json.loads(fallback.read_text(encoding="utf-8-sig"))
        if isinstance(payload, dict):
            return payload
    return {}


def bool_value(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    return default


def unique_in_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def normalize_repo_path(raw: str) -> str:
    return raw.replace("\\", "/").strip().lstrip("./")


def path_is_safe(path: str) -> bool:
    normalized = normalize_repo_path(path)
    return bool(normalized) and ".." not in normalized.split("/") and not Path(normalized).is_absolute() and ".lgwf" not in normalized.split("/")


def _match_facade_docs(path: str) -> bool:
    return path in {
        "skills/lgwf-wf-tools/SKILL.md",
        "skills/lgwf-wf-tools/AGENTS.md",
        "skills/lgwf-wf-tools/README.md",
    }


def extract_workflow_id_from_path(path: str) -> str | None:
    parts = normalize_repo_path(path).split("/")
    marker = ["skills", "lgwf-wf-tools", "workflows"]
    if parts[:3] != marker or len(parts) < 4:
        return None
    workflow_id = parts[3]
    return workflow_id if workflow_id and workflow_id != "01-share" else None


def _rule_matches(path: str, rule_id: str) -> bool:
    path = normalize_repo_path(path)
    if rule_id == "registry_json":
        return path == "skills/lgwf-wf-tools/registry.json"
    if rule_id == "facade_docs":
        return _match_facade_docs(path)
    if rule_id == "shared_contract":
        return path.startswith("skills/lgwf-wf-tools/workflows/01-share/")
    if rule_id == "modular_development_doc":
        return path == "skills/lgwf-wf-tools/docs/LGWF_WF_MODULAR_DEVELOPMENT.md"
    if rule_id == "workflow_entry_contract":
        workflow_id = extract_workflow_id_from_path(path)
        return workflow_id is not None and path.endswith("/entry_contract.json")
    if rule_id == "workflow_source":
        workflow_id = extract_workflow_id_from_path(path)
        return workflow_id is not None and "/wf/" in path
    if rule_id == "workflow_agents":
        workflow_id = extract_workflow_id_from_path(path)
        return workflow_id is not None and path.endswith("/AGENTS.md")
    if rule_id == "workflow_tests":
        workflow_id = extract_workflow_id_from_path(path)
        return workflow_id is not None and "/tests/" in path
    if rule_id == "self_improve":
        return path.startswith("skills/lgwf-wf-tools/workflows/self-improve/")
    if rule_id == "vendor":
        return path.startswith("skills/lgwf-wf-tools/vendor/lgwf-client-assist/")
    if rule_id == "packaging":
        return path in {
            "skills/lgwf-wf-tools/scripts/package_lgwf_wf_tools_zip.py",
            "skills/lgwf-wf-tools/scripts/package_lgwf_skill.py",
        }
    if rule_id == "skill_packaging":
        return path.startswith("skills/lgwf-wf-tools/workflows/skill-packaging/")
    if rule_id == "scripts":
        return path.startswith("skills/lgwf-wf-tools/scripts/")
    if rule_id == "docs_only":
        return path.endswith(".md") or path.startswith("templates/")
    return False


def classify_path(path: str, workflow_ids: list[str] | None = None) -> dict[str, Any]:
    normalized = normalize_repo_path(path)
    matches = [rule for rule in IMPACT_RULES if _rule_matches(normalized, rule["rule_id"])]
    if not matches:
        return {
            "category": "unknown",
            "matched_rules": [],
            "priority": 0,
            "risk": "medium",
            "impacted_workflows": [],
            "recommended_checks": [],
            "rationale": "未命中显式规则，保持人工复核。",
        }

    primary = max(matches, key=lambda item: int(item["priority"]))
    impacted: list[str] = []
    strategy = primary["impacted_workflow_strategy"]
    workflow_id = extract_workflow_id_from_path(normalized)
    if strategy == "all_workflows":
        impacted = list(workflow_ids or [])
    elif strategy == "from_registry_path" and workflow_id:
        impacted = [workflow_id]
    elif strategy == "self_improve":
        impacted = ["self-improve"]
    return {
        "category": primary["category"],
        "matched_rules": [rule["rule_id"] for rule in matches],
        "priority": int(primary["priority"]),
        "risk": max((rule["risk"] for rule in matches), key=lambda item: RISK_ORDER[item]),
        "impacted_workflows": unique_in_order(impacted),
        "recommended_checks": unique_in_order(
            [check for rule in matches for check in rule["recommended_checks"]]
        ),
        "rationale": f"{normalized} 命中 {primary['rule_id']}，主分类为 {primary['category']}。",
    }


def aggregate_impact(files: list[dict[str, Any]]) -> dict[str, Any]:
    categories = unique_in_order([item["category"] for item in files if item.get("category")])
    impacted_workflows = unique_in_order(
        [workflow_id for item in files for workflow_id in item.get("impacted_workflows", [])]
    )
    recommended_checks = unique_in_order(
        [check for item in files for check in item.get("recommended_checks", [])]
    )
    risk = "low"
    for item in files:
        item_risk = str(item.get("risk", "low"))
        if RISK_ORDER.get(item_risk, 0) > RISK_ORDER[risk]:
            risk = item_risk
    ambiguities = [
        f"未识别路径分类：{item['path']}"
        for item in files
        if item.get("category") == "unknown"
    ]
    return {
        "categories": categories,
        "impacted_workflows": impacted_workflows,
        "recommended_checks": recommended_checks,
        "risk": risk,
        "ambiguities": ambiguities,
    }


def build_workflow_test_command(workflow_id: str) -> dict[str, Any]:
    return {
        "check_id": f"workflow_tests:{workflow_id}",
        "command": [
            "python",
            "-m",
            "unittest",
            "discover",
            f"skills/lgwf-wf-tools/workflows/{workflow_id}/tests",
        ],
        "cwd": ".",
        "timeout_seconds": 300,
        "write_effects": [],
        "requires_allow": "allow_workflow_tests",
        "short_circuit": False,
        "failure_type": "test_failure",
    }


def build_verification_plan(impact: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    categories = set(impact.get("categories", []))
    commands: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []

    def allow(name: str, default: bool = False) -> bool:
        return bool_value(request.get(name), default)

    needs_doctor = bool(categories & {"facade_entry", "workflow_source", "shared_contract", "vendor", "packaging", "scripts"})
    if needs_doctor:
        commands.append(dict(COMMAND_TEMPLATES["doctor_basic"], source={"categories": sorted(categories)}))

    wants_deep = bool(
        categories & {"shared_contract", "vendor", "facade_entry"}
        or request.get("verification_level") == "full"
    )
    if wants_deep:
        if allow("allow_deep_doctor", False):
            commands.append(dict(COMMAND_TEMPLATES["deep_doctor"], source={"categories": sorted(categories)}))
        else:
            skipped.append({"check_id": "deep_doctor", "reason": "allow_deep_doctor=false"})

    impacted_workflows = list(impact.get("impacted_workflows", []))
    if impacted_workflows:
        if allow("allow_workflow_tests", True):
            for workflow_id in impacted_workflows:
                commands.append(build_workflow_test_command(workflow_id))
        else:
            skipped.append({"check_id": "workflow_tests", "reason": "allow_workflow_tests=false"})

    if "self_improve" in categories:
        commands.append(dict(COMMAND_TEMPLATES["self_improve_health"], source={"categories": ["self_improve"]}))

    if "self_improve" in categories or request.get("verification_level") == "full":
        if allow("allow_pre_release", False):
            commands.append(dict(COMMAND_TEMPLATES["pre_release"], source={"categories": sorted(categories)}))
        else:
            skipped.append({"check_id": "pre_release", "reason": "allow_pre_release=false"})

    output_zip = request.get("output_zip")
    zip_conflict = {"status": "clear", "path": output_zip, "reason": None}
    wants_package = "packaging" in categories or request.get("intent") == "package_ready"
    if wants_package:
        if not allow("allow_package_smoke", False):
            skipped.append({"check_id": "package_smoke", "reason": "allow_package_smoke=false"})
        elif output_zip:
            commands.append(
                {
                    **COMMAND_TEMPLATES["package_smoke"],
                    "command": [
                        "python",
                        "skills/lgwf-wf-tools/scripts/package_lgwf_wf_tools_zip.py",
                        "--force",
                        "--output",
                        str(output_zip),
                    ],
                    "source": {"categories": sorted(categories)},
                }
            )
        else:
            zip_conflict = {
                "status": "needs_review",
                "path": output_zip,
                "reason": "allow_package_smoke=true 但未提供 output_zip",
            }
            blocked.append({"check_id": "package_smoke", "reason": zip_conflict["reason"]})

    return {
        "artifact_kind": "verification_plan_proposal",
        "request": request,
        "risk": impact.get("risk", "medium"),
        "impacted_workflows": impacted_workflows,
        "commands": commands,
        "blocked_commands": blocked,
        "skipped_or_suggested_checks": skipped,
        "zip_conflict": zip_conflict,
        "requires_confirmation": True,
        "estimated_scope": {
            "command_count": len(commands),
            "skipped_count": len(skipped),
            "blocked_count": len(blocked),
        },
    }


def summarize_output(text: str, limit: int = 8) -> str:
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    if not lines:
        return ""
    selected = lines[:limit]
    return "\n".join(selected)


def route_for_failure(failure_type: str) -> dict[str, Any]:
    mapped = FAILURE_ROUTE_RULES.get(
        failure_type,
        {"route": "needs_review", "reason": "未映射失败类型，保持人工复核"},
    )
    return {"failure_type": failure_type, **mapped}


def derive_gate_status(
    verification_results: dict[str, Any],
    ambiguities: list[str] | None = None,
    high_risk_skips: list[str] | None = None,
) -> str:
    ambiguities = ambiguities or []
    high_risk_skips = high_risk_skips or []
    failures = verification_results.get("commands", [])
    if any(item.get("status") == "fail" and item.get("failure_type") not in {"timeout", "command_contract"} for item in failures):
        return "fail"
    if ambiguities or high_risk_skips:
        return "needs_review"
    if any(item.get("failure_type") in {"timeout", "command_contract"} for item in failures):
        return "needs_review"
    return "pass"
