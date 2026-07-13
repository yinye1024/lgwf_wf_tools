from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REQUEST_PATH = Path(".lgwf") / "repo_context_pack_request.json"
INVENTORY_PATH = Path(".lgwf") / "context_inventory.json"
GENERATION_PATH = Path(".lgwf") / "context_pack_generation.json"
ARTIFACT_DIR = Path("reports") / "repo-context-pack"
MARKDOWN_PATH = ARTIFACT_DIR / "repo-context-pack.md"
JSON_PATH = ARTIFACT_DIR / "repo-context-pack.json"
INDEX_PATH = ARTIFACT_DIR / "artifact-index.json"


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path.as_posix()} 必须是 JSON object。")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def normalize_request(payload: dict[str, Any]) -> dict[str, Any]:
    request = payload.get("request")
    if isinstance(request, dict):
        return request
    return payload


def normalize_inventory(payload: dict[str, Any]) -> dict[str, Any]:
    for key in ("context_inventory", "inventory", "result"):
        candidate = payload.get(key)
        if isinstance(candidate, dict):
            return candidate
    return payload


def flatten_named_records(value: Any) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if isinstance(value, list):
        for index, item in enumerate(value, start=1):
            if isinstance(item, dict):
                record = dict(item)
                record.setdefault("name", record.get("id") or record.get("path") or f"item-{index}")
                records.append(record)
            else:
                records.append({"name": f"item-{index}", "value": item})
        return records

    if isinstance(value, dict):
        if any(key in value for key in ("items", "entries", "results")):
            for key in ("items", "entries", "results"):
                if key in value:
                    return flatten_named_records(value[key])
        for key in sorted(value):
            item = value[key]
            if isinstance(item, dict):
                record = dict(item)
                record.setdefault("name", key)
                records.append(record)
            else:
                records.append({"name": key, "value": item})
        return records

    if value is None:
        return records

    return [{"name": "value", "value": value}]


def pick_first(payload: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in payload:
            return payload[key]
    return None


def collect_commands(inventory: dict[str, Any]) -> list[dict[str, Any]]:
    commands: list[dict[str, Any]] = []
    for key in ("commands", "run_commands", "test_commands", "cli_commands"):
        commands.extend(flatten_named_records(inventory.get(key)))
    return commands


def collect_risks(request: dict[str, Any], inventory: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for source in (
        request.get("risks"),
        request.get("constraints"),
        inventory.get("risks"),
        inventory.get("constraints"),
        inventory.get("warnings"),
    ):
        for item in as_list(source):
            if isinstance(item, str) and item.strip():
                values.append(item.strip())
            elif isinstance(item, dict):
                summary = item.get("summary") or item.get("message") or item.get("name")
                if isinstance(summary, str) and summary.strip():
                    values.append(summary.strip())
    deduped: list[str] = []
    seen: set[str] = set()
    for item in values:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped


def collect_truncation_notes(inventory: dict[str, Any]) -> list[str]:
    notes: list[str] = []
    for key in ("truncation", "truncation_notes", "omissions", "gaps"):
        value = inventory.get(key)
        if isinstance(value, str) and value.strip():
            notes.append(value.strip())
            continue
        for item in as_list(value):
            if isinstance(item, str) and item.strip():
                notes.append(item.strip())
            elif isinstance(item, dict):
                summary = item.get("summary") or item.get("reason") or item.get("name")
                if isinstance(summary, str) and summary.strip():
                    notes.append(summary.strip())
    return notes


def summarize_request(request: dict[str, Any]) -> dict[str, Any]:
    return {
        "goal": pick_first(request, ("goal", "objective", "summary", "title")),
        "target": pick_first(request, ("target", "target_path", "target_dir", "target_repo")),
        "raw_intent": pick_first(request, ("raw_intent", "description")),
        "expected_outputs": pick_first(request, ("expected_outputs", "deliverables", "artifacts")),
    }


def build_render_plan(request: dict[str, Any], inventory: dict[str, Any]) -> dict[str, Any]:
    module_records = flatten_named_records(
        pick_first(inventory, ("modules", "module_mapping", "module_map", "packages"))
    )
    entrypoint_records = flatten_named_records(
        pick_first(inventory, ("entrypoints", "entry_points", "detected_entrypoints"))
    )
    command_records = collect_commands(inventory)
    risk_records = collect_risks(request, inventory)
    truncation_notes = collect_truncation_notes(inventory)

    return {
        "stage_id": "context_pack_rendering",
        "artifact_dir": ARTIFACT_DIR.as_posix(),
        "request_summary": summarize_request(request),
        "inventory_summary": {
            "module_count": len(module_records),
            "entrypoint_count": len(entrypoint_records),
            "command_count": len(command_records),
            "risk_count": len(risk_records),
            "truncation_note_count": len(truncation_notes),
        },
        "sections": [
            "请求摘要",
            "目标范围",
            "模块与入口",
            "命令线索",
            "风险与限制",
            "截断与缺口",
            "产物索引",
        ],
        "artifacts": [
            {
                "path": MARKDOWN_PATH.as_posix(),
                "type": "markdown",
                "description": "供人类快速阅读的仓库上下文包摘要。",
            },
            {
                "path": JSON_PATH.as_posix(),
                "type": "json",
                "description": "供下游自动化流程消费的结构化上下文包。",
            },
            {
                "path": INDEX_PATH.as_posix(),
                "type": "json",
                "description": "记录本阶段实际产物路径与说明的索引。",
            },
        ],
    }


def render_bullet_lines(records: list[Any], fallback: str) -> list[str]:
    if not records:
        return [f"- {fallback}"]

    lines: list[str] = []
    for record in records:
        if isinstance(record, dict):
            name = record.get("name") or record.get("id") or record.get("path") or "未命名项"
            summary = record.get("summary") or record.get("description") or record.get("value")
            if summary is None:
                lines.append(f"- `{name}`")
            else:
                lines.append(f"- `{name}`: {summary}")
        else:
            lines.append(f"- {record}")
    return lines


def render_markdown(
    request: dict[str, Any],
    inventory: dict[str, Any],
    plan: dict[str, Any],
) -> str:
    module_records = flatten_named_records(
        pick_first(inventory, ("modules", "module_mapping", "module_map", "packages"))
    )
    entrypoint_records = flatten_named_records(
        pick_first(inventory, ("entrypoints", "entry_points", "detected_entrypoints"))
    )
    command_records = collect_commands(inventory)
    risk_records = collect_risks(request, inventory)
    truncation_notes = collect_truncation_notes(inventory)
    request_summary = plan["request_summary"]

    scope_lines = render_bullet_lines(
        flatten_named_records(
            pick_first(inventory, ("targets", "target_paths", "scanned_paths", "analysis_targets"))
        ),
        "上游 inventory 未提供显式目标路径清单。",
    )
    module_lines = render_bullet_lines(module_records, "未检测到模块映射。")
    entrypoint_lines = render_bullet_lines(entrypoint_records, "未检测到入口线索。")
    command_lines = render_bullet_lines(command_records, "未检测到命令线索。")
    artifact_lines = render_bullet_lines(plan["artifacts"], "未生成产物索引。")

    risk_lines = [f"- {item}" for item in risk_records] or ["- 当前 inventory 未提供显式风险。"]
    truncation_lines = [f"- {item}" for item in truncation_notes] or ["- 当前 inventory 未声明截断或缺口。"]

    request_goal = request_summary.get("goal") or "未提供目标摘要。"
    request_target = request_summary.get("target") or "未提供目标路径。"
    request_intent = request_summary.get("raw_intent") or "未提供额外原始意图。"

    lines = [
        "# Repo Context Pack",
        "",
        "## 请求摘要",
        f"- 目标：{request_goal}",
        f"- 目标对象：{request_target}",
        f"- 原始意图：{request_intent}",
        f"- 输出目录：`{ARTIFACT_DIR.as_posix()}`",
        "",
        "## 目标范围",
        *scope_lines,
        "",
        "## 模块与入口",
        "### 模块映射",
        *module_lines,
        "",
        "### 入口线索",
        *entrypoint_lines,
        "",
        "## 命令线索",
        *command_lines,
        "",
        "## 风险与限制",
        *risk_lines,
        "",
        "## 截断与缺口",
        *truncation_lines,
        "",
        "## 产物索引",
        *artifact_lines,
        "",
        "## 原始统计",
        f"- 模块数：{plan['inventory_summary']['module_count']}",
        f"- 入口数：{plan['inventory_summary']['entrypoint_count']}",
        f"- 命令数：{plan['inventory_summary']['command_count']}",
        f"- 风险数：{plan['inventory_summary']['risk_count']}",
        f"- 截断说明数：{plan['inventory_summary']['truncation_note_count']}",
        "",
    ]
    return "\n".join(lines)


def build_json_artifact(
    request: dict[str, Any],
    inventory: dict[str, Any],
    plan: dict[str, Any],
) -> dict[str, Any]:
    return {
        "artifact_type": "repo_context_pack",
        "stage_id": "context_pack_rendering",
        "request": request,
        "inventory": inventory,
        "render_plan": plan,
        "artifacts": plan["artifacts"],
    }


def build_index(plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "artifact_dir": ARTIFACT_DIR.as_posix(),
        "items": plan["artifacts"],
    }


def build_generation_result(
    request: dict[str, Any],
    inventory: dict[str, Any],
    plan: dict[str, Any],
) -> dict[str, Any]:
    requested_output_dir = pick_first(request, ("output_dir", "resolved_output_dir"))
    notes = []
    if requested_output_dir and requested_output_dir != ARTIFACT_DIR.as_posix():
        notes.append(
            "首版实现固定写入 reports/repo-context-pack；request 中的自定义 output_dir 仅保留为说明信息。"
        )

    return {
        "stage_id": "context_pack_rendering",
        "status": "ok",
        "request_summary": plan["request_summary"],
        "inventory_summary": plan["inventory_summary"],
        "artifact_dir": ARTIFACT_DIR.as_posix(),
        "requested_output_dir": requested_output_dir,
        "artifacts": plan["artifacts"],
        "notes": notes,
    }


def main() -> int:
    request_payload = read_json(REQUEST_PATH)
    inventory_payload = read_json(INVENTORY_PATH)

    request = normalize_request(request_payload)
    inventory = normalize_inventory(inventory_payload)
    plan = build_render_plan(request, inventory)

    markdown = render_markdown(request, inventory, plan)
    json_artifact = build_json_artifact(request, inventory, plan)
    artifact_index = build_index(plan)
    generation_result = build_generation_result(request, inventory, plan)

    write_text(MARKDOWN_PATH, markdown)
    write_json(JSON_PATH, json_artifact)
    write_json(INDEX_PATH, artifact_index)
    write_json(GENERATION_PATH, generation_result)

    json.dump(generation_result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
