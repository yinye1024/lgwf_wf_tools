from __future__ import annotations

from typing import Any


TARGET_TYPES = {"create_artifact", "modify_artifact", "execute_process", "analyze", "fix", "review"}
TASK_ROLES = {"implementation_action", "validation_action", "generated_artifact_behavior", "human_decision"}
FUTURE_SUBJECTS = {"generated_artifact_runtime", "future_runtime", "target_runtime"}
FUTURE_RUNTIME_ARTIFACT_MARKERS = (
    ".lgwf/create_requirements",
    ".lgwf/business_flow",
    ".lgwf/step_designs",
    ".lgwf/raw_intent",
    ".lgwf/scaffold_result",
    ".lgwf/create_summary",
)


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _target_type(request: dict[str, Any], plan: dict[str, Any]) -> str:
    for source in (request, plan.get("summary") if isinstance(plan.get("summary"), dict) else {}):
        raw = _text(source.get("target_type")).lower()
        if raw in TARGET_TYPES:
            return raw
    return "unspecified"


def validate_plan_contract(request: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    """Return deterministic safety findings for the generated plan contract."""
    target_type = _target_type(request, plan)
    issues: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    tasks = [task for task in plan.get("tasks", []) if isinstance(task, dict)]

    if target_type == "create_artifact":
        for index, task in enumerate(tasks):
            task_id = _text(task.get("task_id")) or f"task[{index}]"
            role = _text(task.get("task_role")).lower()
            subject = _text(task.get("execution_subject")).lower()
            artifacts = _as_list(task.get("produced_artifacts"))

            if role not in TASK_ROLES:
                issues.append(
                    {
                        "task_id": task_id,
                        "code": "missing_or_invalid_task_role",
                        "message": "create_artifact 目标下，每个 task 必须声明有效 task_role。",
                    }
                )
                continue

            if role == "generated_artifact_behavior":
                issues.append(
                    {
                        "task_id": task_id,
                        "code": "generated_artifact_behavior_in_current_plan",
                        "message": "目标产物将来的内部行为不能作为当前 lgwf-plan run 的执行 task。",
                    }
                )

            if subject in FUTURE_SUBJECTS:
                issues.append(
                    {
                        "task_id": task_id,
                        "code": "future_runtime_subject_in_current_plan",
                        "message": "execution_subject 指向未来运行时，疑似把目标产物内部流程当成当前任务执行。",
                    }
                )

            if role in {"implementation_action", "validation_action"} and not artifacts:
                warnings.append(
                    {
                        "task_id": task_id,
                        "code": "missing_produced_artifacts",
                        "message": "当前执行 task 应声明会产生或验证的目标 artifact 文件、目录、代码、配置或文档。",
                    }
                )

            artifact_text = "\n".join(_text(item).replace("\\", "/") for item in artifacts).lower()
            if any(marker in artifact_text for marker in FUTURE_RUNTIME_ARTIFACT_MARKERS):
                issues.append(
                    {
                        "task_id": task_id,
                        "code": "future_runtime_artifact_in_current_outputs",
                        "message": "create_artifact 当前 task 不能把目标 workflow 未来运行时的 .lgwf 产物列为当前 produced_artifacts。",
                    }
                )

    return {
        "target_type": target_type,
        "passed": not issues,
        "issues": issues,
        "warnings": warnings,
    }
