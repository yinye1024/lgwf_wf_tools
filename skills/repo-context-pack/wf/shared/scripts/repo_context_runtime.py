from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


FOCUS_VALUES = {"onboarding", "modification", "review", "workflow-authoring", "handoff"}
DEPTH_VALUES = {"light", "normal", "deep"}
ARTIFACT_NAMES = [
    "repo_context_pack.md",
    "agent_handoff.md",
    "module_map.json",
    "command_inventory.json",
    "risk_register.md",
    "read_order.md",
    "summary.json",
]


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


def read_stdin_payload() -> dict[str, Any]:
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    data = json.loads(raw)
    if not isinstance(data, dict):
        return {}
    for key in ("repo_context_pack", "request"):
        value = data.get(key)
        if isinstance(value, dict):
            return value
    return data


def find_package_root(script_path: Path) -> Path:
    for candidate in [script_path.resolve(), *script_path.resolve().parents]:
        if (candidate / "scripts" / "build_context_pack.py").is_file() and (candidate / "wf").is_dir():
            return candidate
    raise RuntimeError(f"无法定位 repo-context-pack package root: {script_path}")


def load_builder(package_root: Path) -> Any:
    script = package_root / "scripts" / "build_context_pack.py"
    spec = importlib.util.spec_from_file_location("repo_context_pack_builder", script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载上下文包构建脚本: {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def unwrap_request(raw: dict[str, Any]) -> dict[str, Any]:
    for key in ("repo_context_pack", "request"):
        value = raw.get(key)
        if isinstance(value, dict):
            return value
    return raw


def normalize_request(package_root: Path, raw: dict[str, Any]) -> dict[str, Any]:
    request = unwrap_request(raw)
    target_raw = str(request.get("target_dir", "")).strip()
    if not target_raw:
        raise ValueError("repo-context-pack 需要输入 target_dir")
    target_dir = Path(target_raw).expanduser().resolve()
    if not target_dir.is_dir():
        raise ValueError(f"target_dir 不存在或不是目录: {target_dir}")

    output_raw = str(request.get("output_dir", "")).strip()
    if output_raw:
        output_dir = Path(output_raw).expanduser().resolve()
    else:
        output_dir = (target_dir / ".local" / "context-packs" / target_dir.name).resolve()

    focus = str(request.get("focus") or "onboarding").strip()
    if focus not in FOCUS_VALUES:
        raise ValueError(f"focus 不支持: {focus}")
    depth = str(request.get("depth") or "normal").strip()
    if depth not in DEPTH_VALUES:
        raise ValueError(f"depth 不支持: {depth}")
    try:
        max_files = int(request.get("max_files", 1600))
    except (TypeError, ValueError) as exc:
        raise ValueError("max_files 必须是整数") from exc
    if max_files < 1:
        raise ValueError("max_files 必须大于 0")

    return {
        "target_dir": str(target_dir),
        "output_dir": str(output_dir),
        "focus": focus,
        "depth": depth,
        "max_files": max_files,
        "notes": str(request.get("notes", "")).strip(),
        "package_root": str(package_root),
    }


def request_path() -> Path:
    return Path.cwd() / ".lgwf" / "repo_context_pack_request.json"


def inventory_path() -> Path:
    return Path.cwd() / ".lgwf" / "context_inventory.json"


def generation_path() -> Path:
    return Path.cwd() / ".lgwf" / "context_pack_generation.json"


def summary_path() -> Path:
    return Path.cwd() / ".lgwf" / "repo_context_pack_summary.json"


def load_request() -> dict[str, Any]:
    request = read_json(request_path())
    if not request:
        raise ValueError("缺少 .lgwf/repo_context_pack_request.json，请先运行 entry_scope_resolution")
    return request


def collect_inventory(package_root: Path, request: dict[str, Any]) -> dict[str, Any]:
    builder = load_builder(package_root)
    target_dir = Path(request["target_dir"]).resolve()
    dirs, files = builder.walk_target(target_dir, request["depth"], int(request["max_files"]))
    entry_files = builder.detect_entry_files(target_dir, files)
    modules = builder.detect_modules(target_dir, dirs)
    commands = builder.extract_commands(target_dir, files)
    risks = builder.extract_risks(target_dir, files)
    read_order = builder.build_read_order(request["focus"], entry_files, modules)
    return {
        "target_dir": str(target_dir),
        "focus": request["focus"],
        "depth": request["depth"],
        "scanned_file_count": len(files),
        "entry_files": entry_files,
        "modules": modules,
        "commands": commands,
        "risks": risks,
        "read_order": read_order,
    }


def render_pack(package_root: Path, request: dict[str, Any]) -> dict[str, Any]:
    builder = load_builder(package_root)
    args = argparse.Namespace(
        target_dir=request["target_dir"],
        output_dir=request["output_dir"],
        focus=request["focus"],
        depth=request["depth"],
        max_files=int(request["max_files"]),
    )
    return builder.build_pack(args)


def validate_outputs(output_dir: Path) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for name in ARTIFACT_NAMES:
        path = output_dir / name
        item = {"path": name, "exists": path.is_file()}
        if name.endswith(".json") and path.is_file():
            json.loads(path.read_text(encoding="utf-8-sig"))
            item["json_ok"] = True
        checks.append(item)
    return checks


def run_stage(stage_id: str, script_path: Path) -> None:
    package_root = find_package_root(script_path)
    if stage_id == "entry_scope_resolution":
        request = normalize_request(package_root, read_stdin_payload())
        write_json(request_path(), request)
        payload = {"repo_context_pack.request": request}
    elif stage_id == "target_context_inventory":
        request = load_request()
        inventory = collect_inventory(package_root, request)
        write_json(inventory_path(), inventory)
        payload = {"repo_context_pack.context_inventory": inventory}
    elif stage_id == "context_pack_rendering":
        request = load_request()
        inventory = read_json(inventory_path())
        summary = render_pack(package_root, request)
        result = {"summary": summary, "inventory_available": bool(inventory)}
        write_json(generation_path(), result)
        payload = {"repo_context_pack.generation": result}
    elif stage_id == "workflow_summary_handoff":
        request = load_request()
        generation = read_json(generation_path())
        output_dir = Path(request["output_dir"]).resolve()
        checks = validate_outputs(output_dir)
        passed = all(item["exists"] for item in checks)
        summary = read_json(output_dir / "summary.json")
        result = {
            "passed": passed,
            "request": request,
            "generation": generation,
            "output_dir": str(output_dir),
            "artifacts": checks,
            "summary": summary,
        }
        write_json(summary_path(), result)
        report_lines = [
            "# repo-context-pack 运行报告",
            "",
            f"- 状态：`{'passed' if passed else 'failed'}`",
            f"- 目标目录：`{request['target_dir']}`",
            f"- 输出目录：`{output_dir}`",
            "",
            "## 产物",
            "",
            *[f"- `{item['path']}`：{'存在' if item['exists'] else '缺失'}" for item in checks],
            "",
        ]
        write_text(Path.cwd() / "reports" / "repo-context-pack" / "report.md", "\n".join(report_lines))
        payload = {"repo_context_pack.summary": result}
    else:
        raise ValueError(f"未知阶段: {stage_id}")

    print(json.dumps(payload, ensure_ascii=False, indent=2))
