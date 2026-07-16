"""wf-convert Observe 报告的统一协议与合并逻辑。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = 1
ALLOWED_SEVERITIES = {"high", "medium", "low"}
ALLOWED_OBSERVERS = {"python", "codex", "protocol"}
ALLOWED_OBSERVER_STATUSES = {"pass", "revise", "invalid"}
STAGE_ARTIFACTS = {
    "inspection": ".lgwf/prompt_workflow_inspection.json",
    "proposal": ".lgwf/wf_create_fast_input_proposal.json",
}


def read_json_object(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise TypeError(f"{path.as_posix()} 必须是 JSON object")
    return data


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def make_issue(
    *,
    observer: str,
    code: str,
    field: str,
    blocking: bool,
    severity: str,
    issue: str,
    required_change: str,
) -> dict[str, Any]:
    return {
        "observer": observer,
        "code": code,
        "field": field,
        "blocking": blocking,
        "severity": severity,
        "issue": issue,
        "required_change": required_change,
    }


def build_observer_report(
    *,
    stage: str,
    observer: str,
    issues: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    normalized_issues = list(issues)
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": stage,
        "observer": observer,
        "issues": normalized_issues,
    }


def _protocol_issue(field: str, issue: str, required_change: str) -> dict[str, Any]:
    return make_issue(
        observer="protocol",
        code="INVALID_OBSERVER_REPORT",
        field=field,
        blocking=True,
        severity="high",
        issue=issue,
        required_change=required_change,
    )


def _normalize_report(
    *,
    path: Path,
    expected_stage: str,
    expected_observer: str,
) -> tuple[str, list[dict[str, Any]]]:
    try:
        report = read_json_object(path)
    except (FileNotFoundError, json.JSONDecodeError, TypeError) as exc:
        return "invalid", [
            _protocol_issue(
                path.name,
                f"{expected_observer} Observe 报告缺失或无法解析：{exc}",
                f"重新执行 {expected_observer} Observe 并写入合法 JSON 报告",
            )
        ]

    issues: list[dict[str, Any]] = []
    if report.get("schema_version") != SCHEMA_VERSION:
        issues.append(
            _protocol_issue(
                "schema_version",
                f"{expected_observer} Observe schema_version 非 {SCHEMA_VERSION}",
                f"按 Observe 协议版本 {SCHEMA_VERSION} 重新输出",
            )
        )
    if report.get("stage") != expected_stage:
        issues.append(
            _protocol_issue(
                "stage",
                f"{expected_observer} Observe stage 与 {expected_stage} 不一致",
                f"把 stage 固定为 {expected_stage}",
            )
        )
    if report.get("observer") != expected_observer:
        issues.append(
            _protocol_issue(
                "observer",
                f"Observer 标识必须为 {expected_observer}",
                f"把 observer 固定为 {expected_observer}",
            )
        )

    raw_issues = report.get("issues")
    if not isinstance(raw_issues, list):
        issues.append(
            _protocol_issue(
                "issues",
                f"{expected_observer} Observe issues 必须是数组",
                "输出结构化 issues 数组；无问题时输出空数组",
            )
        )
        return "invalid", issues

    required_fields = {
        "observer",
        "code",
        "field",
        "blocking",
        "severity",
        "issue",
        "required_change",
    }
    for index, item in enumerate(raw_issues):
        field_prefix = f"issues[{index}]"
        if not isinstance(item, dict):
            issues.append(
                _protocol_issue(
                    field_prefix,
                    "Observe issue 必须是 JSON object",
                    "按统一 issue 协议重新输出",
                )
            )
            continue
        missing = sorted(required_fields - set(item))
        if missing:
            issues.append(
                _protocol_issue(
                    field_prefix,
                    f"Observe issue 缺少字段：{', '.join(missing)}",
                    "补齐 observer、code、field、blocking、severity、issue 和 required_change",
                )
            )
            continue
        if item.get("observer") != expected_observer:
            issues.append(
                _protocol_issue(
                    f"{field_prefix}.observer",
                    f"issue observer 必须为 {expected_observer}",
                    f"把 observer 固定为 {expected_observer}",
                )
            )
            continue
        if not isinstance(item.get("blocking"), bool):
            issues.append(
                _protocol_issue(
                    f"{field_prefix}.blocking",
                    "blocking 必须是布尔值",
                    "根据是否阻塞下一阶段写入 true 或 false",
                )
            )
            continue
        if item.get("severity") not in ALLOWED_SEVERITIES:
            issues.append(
                _protocol_issue(
                    f"{field_prefix}.severity",
                    "severity 必须是 high、medium 或 low",
                    "改用允许的严重度枚举",
                )
            )
            continue
        if not all(str(item.get(key, "")).strip() for key in ("code", "field", "issue", "required_change")):
            issues.append(
                _protocol_issue(
                    field_prefix,
                    "code、field、issue 和 required_change 不得为空",
                    "补充可定位、可执行的问题描述",
                )
            )
            continue
        issues.append(dict(item))

    status = "invalid" if any(item["observer"] == "protocol" for item in issues) else (
        "revise" if raw_issues else "pass"
    )
    return status, issues


def merge_observer_reports(
    *,
    stage: str,
    artifact_path: Path,
    python_report_path: Path,
    codex_report_path: Path,
) -> dict[str, Any]:
    python_status, python_issues = _normalize_report(
        path=python_report_path,
        expected_stage=stage,
        expected_observer="python",
    )
    codex_status, codex_issues = _normalize_report(
        path=codex_report_path,
        expected_stage=stage,
        expected_observer="codex",
    )
    issues = python_issues + codex_issues
    artifact_sha256 = ""
    try:
        artifact_sha256 = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    except FileNotFoundError:
        issues.append(
            _protocol_issue(
                artifact_path.name,
                "被审查产物不存在，不能生成可信 Observe",
                "重新执行 Act 并确保业务产物已经写入",
            )
        )

    blocking = any(item.get("blocking") is True for item in issues)
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": stage,
        "artifact": {
            "path": f".lgwf/{artifact_path.name}",
            "sha256": artifact_sha256,
        },
        "verdict": "revise" if issues else "pass",
        "blocking": blocking,
        "observer_status": {
            "python": python_status,
            "codex": codex_status,
        },
        "issues": issues,
    }


def decide_next(observe_path: Path, *, expected_stage: str) -> str:
    try:
        observe = read_json_object(observe_path)
    except (FileNotFoundError, json.JSONDecodeError, TypeError):
        return "continue"
    if observe.get("schema_version") != SCHEMA_VERSION:
        return "continue"
    if observe.get("stage") != expected_stage:
        return "continue"
    artifact = observe.get("artifact")
    if not isinstance(artifact, dict):
        return "continue"
    if artifact.get("path") != STAGE_ARTIFACTS.get(expected_stage):
        return "continue"
    artifact_sha256 = artifact.get("sha256")
    if (
        not isinstance(artifact_sha256, str)
        or len(artifact_sha256) != 64
        or any(char not in "0123456789abcdef" for char in artifact_sha256)
    ):
        return "continue"
    if not isinstance(observe.get("blocking"), bool):
        return "continue"
    observer_status = observe.get("observer_status")
    if not isinstance(observer_status, dict) or set(observer_status) != {"python", "codex"}:
        return "continue"
    if any(status not in ALLOWED_OBSERVER_STATUSES for status in observer_status.values()):
        return "continue"
    issues = observe.get("issues")
    if not isinstance(issues, list):
        return "continue"
    required_issue_fields = {
        "observer",
        "code",
        "field",
        "blocking",
        "severity",
        "issue",
        "required_change",
    }
    for issue in issues:
        if not isinstance(issue, dict) or not required_issue_fields.issubset(issue):
            return "continue"
        if issue.get("observer") not in ALLOWED_OBSERVERS:
            return "continue"
        if not isinstance(issue.get("blocking"), bool):
            return "continue"
        if issue.get("severity") not in ALLOWED_SEVERITIES:
            return "continue"
        if not all(
            isinstance(issue.get(key), str) and issue[key].strip()
            for key in ("code", "field", "issue", "required_change")
        ):
            return "continue"
    derived_blocking = any(issue.get("blocking") is True for issue in issues)
    if derived_blocking != observe["blocking"]:
        return "continue"
    expected_verdict = "revise" if issues else "pass"
    if observe.get("verdict") != expected_verdict:
        return "continue"
    return "continue" if observe["blocking"] else "exit"
