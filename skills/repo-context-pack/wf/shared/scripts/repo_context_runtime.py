from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


FOCUS_VALUES = {"onboarding", "modification", "review", "workflow-authoring", "handoff"}
DEPTH_VALUES = {"light", "normal", "deep"}
DEPTH_TO_MAX_DEPTH = {"light": 2, "normal": 4, "deep": 8}
ARTIFACT_NAMES = [
    "repo_context_pack.md",
    "agent_handoff.md",
    "module_map.json",
    "command_inventory.json",
    "risk_register.md",
    "read_order.md",
    "summary.json",
]
SKIP_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    ".lgwf",
    ".local",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "__pycache__",
    "dist",
    "build",
    "coverage",
    "outputs",
    "docs_tmp",
    "tmp",
    "temp",
    "vendor",
    "ws",
}
ENTRY_FILE_NAMES = {
    "AGENTS.md",
    "README.md",
    "SKILL.md",
    "package.json",
    "pyproject.toml",
    "setup.cfg",
    "setup.py",
    "requirements.txt",
    "registry.json",
    "entry_contract.json",
    "workflow.lgwf",
    "Dockerfile",
    "Makefile",
}
TEXT_SUFFIXES = {
    ".md",
    ".txt",
    ".json",
    ".toml",
    ".yaml",
    ".yml",
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".ps1",
    ".sh",
    ".lgwf",
}
COMMAND_RE = re.compile(
    r"^\s*(?:PS>\s*|\$\s*)?"
    r"(?P<cmd>(?:python|py|pytest|ruff|mypy|npm|pnpm|yarn|uv|git|node|npx|docker|make|pwsh|powershell)\b.+|(?:\.{0,2}[\\/])?[\w./\\:-]*lgwf\.py\b.+)",
    re.IGNORECASE,
)
RISK_RE = re.compile(r"(禁止|不得|不要|必须|只允许|状态边界|UTF-8|no BOM|approval|vendor|\.lgwf|work_dir|work dir)")


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
        fallback = Path.cwd() / ".lgwf" / "input_state.json"
        if fallback.is_file():
            data = json.loads(fallback.read_text(encoding="utf-8-sig"))
            return data if isinstance(data, dict) else {}
        return {}
    data = json.loads(raw)
    if not isinstance(data, dict):
        return {}
    for key in ("repo_context_pack", "request"):
        value = data.get(key)
        if isinstance(value, dict):
            return value
    return data


def rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def is_text_candidate(path: Path) -> bool:
    if path.name in ENTRY_FILE_NAMES:
        return True
    return path.suffix.lower() in TEXT_SUFFIXES


def should_skip_dir(path: Path) -> bool:
    return path.name in SKIP_DIR_NAMES or path.name.endswith(".egg-info")


def walk_target(root: Path, depth: str, max_files: int) -> tuple[list[Path], list[Path]]:
    max_depth = DEPTH_TO_MAX_DEPTH[depth]
    dirs: list[Path] = [root]
    files: list[Path] = []
    for current, dirnames, filenames in os.walk(root):
        current_path = Path(current)
        current_depth = len(current_path.relative_to(root).parts)
        dirnames[:] = sorted(d for d in dirnames if not should_skip_dir(current_path / d))
        if current_depth >= max_depth:
            dirnames[:] = []
        dirs.extend(current_path / d for d in dirnames)
        for filename in sorted(filenames):
            path = current_path / filename
            if not is_text_candidate(path):
                continue
            files.append(path)
            if len(files) >= max_files:
                return dirs, files
    return dirs, files


def read_small_text(path: Path, limit: int = 256_000) -> str:
    try:
        if path.stat().st_size > limit:
            return ""
        return path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""


def detect_entry_files(root: Path, files: list[Path]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path in files:
        if path.name in ENTRY_FILE_NAMES:
            entries.append({"path": rel(path, root), "kind": path.name})
    return sorted(entries, key=lambda item: item["path"])


def detect_modules(root: Path, dirs: list[Path]) -> list[dict[str, Any]]:
    modules: list[dict[str, Any]] = []
    seen: set[str] = set()
    for directory in sorted(dirs):
        if directory.name == "wf" and (directory.parent / "entry_contract.json").exists():
            continue
        kind = None
        entry_files: list[str] = []
        if (directory / "SKILL.md").exists():
            kind = "codex_skill"
            entry_files.append("SKILL.md")
        if (directory / "entry_contract.json").exists() and (
            (directory / "wf" / "workflow.lgwf").exists() or (directory / "workflow.lgwf").exists()
        ):
            kind = "lgwf_workflow_package"
            entry_files.append("entry_contract.json")
        if (directory / "wf" / "workflow.lgwf").exists():
            kind = kind or "lgwf_embedded_workflow"
            entry_files.append("wf/workflow.lgwf")
        if (directory / "workflow.lgwf").exists():
            kind = kind or "lgwf_workflow_root"
            entry_files.append("workflow.lgwf")
        if (directory / "pyproject.toml").exists() or (directory / "setup.py").exists():
            kind = kind or "python_project"
            for name in ("pyproject.toml", "setup.py"):
                if (directory / name).exists():
                    entry_files.append(name)
        if (directory / "package.json").exists():
            kind = kind or "node_project"
            entry_files.append("package.json")
        if kind is None:
            continue

        module_path = "." if directory == root else rel(directory, root)
        if module_path in seen:
            continue
        seen.add(module_path)
        modules.append(
            {
                "path": module_path,
                "kind": kind,
                "entry_files": sorted(set(entry_files)),
                "has_agents_md": (directory / "AGENTS.md").exists(),
                "has_readme": (directory / "README.md").exists(),
                "tests": "tests" if (directory / "tests").exists() else None,
            }
        )
    return modules


def infer_commands(root: Path) -> list[dict[str, Any]]:
    inferred: list[dict[str, Any]] = []
    if (root / "pyproject.toml").exists() or (root / "tests").exists():
        inferred.append({"command": "python -m unittest discover tests", "source": "inferred", "line": None, "inferred": True})
    if (root / "package.json").exists():
        inferred.extend(
            [
                {"command": "npm test", "source": "inferred", "line": None, "inferred": True},
                {"command": "npm run build", "source": "inferred", "line": None, "inferred": True},
            ]
        )
    if (root / "registry.json").exists() or (root / "skills" / "lgwf-wf-tools" / "registry.json").exists():
        inferred.append(
            {
                "command": "python skills\\lgwf-wf-tools\\scripts\\doctor_lgwf_wf_tools.py",
                "source": "inferred",
                "line": None,
                "inferred": True,
            }
        )
    return inferred


def extract_commands(root: Path, files: list[Path]) -> list[dict[str, Any]]:
    commands: dict[str, dict[str, Any]] = {}
    for path in files:
        if path.suffix.lower() not in {".md", ".txt"} and path.name not in {"README.md", "AGENTS.md", "SKILL.md"}:
            continue
        text = read_small_text(path)
        if not text:
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            candidate = re.sub(r"^[-*]\s+", "", line.strip()).strip("` ")
            match = COMMAND_RE.match(candidate)
            if not match:
                continue
            command = match.group("cmd").strip().rstrip("`")
            if len(command) > 280:
                continue
            commands.setdefault(
                command.lower(),
                {"command": command, "source": rel(path, root), "line": line_number, "inferred": False},
            )

    for item in infer_commands(root):
        commands.setdefault(item["command"].lower(), item)
    return sorted(commands.values(), key=lambda item: (item.get("inferred", False), item["source"], item["command"]))


def extract_risks(root: Path, files: list[Path]) -> list[dict[str, Any]]:
    risks: list[dict[str, Any]] = [
        {"source": "builtin", "line": None, "text": "默认只读 target_dir，只向 output_dir 写入上下文包。"},
        {"source": "builtin", "line": None, "text": "跳过运行态、缓存和依赖目录，避免把大体量或临时状态塞进上下文。"},
        {"source": "builtin", "line": None, "text": "生成的 Markdown 和 JSON 必须保持 UTF-8 no BOM。"},
    ]
    for path in files:
        if path.name not in {"AGENTS.md", "README.md", "SKILL.md"}:
            continue
        text = read_small_text(path)
        if not text:
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if len(stripped) < 8 or len(stripped) > 220:
                continue
            if RISK_RE.search(stripped):
                risks.append({"source": rel(path, root), "line": line_number, "text": stripped.lstrip("- ")})
            if len(risks) >= 40:
                return risks
    return risks


def build_read_order(focus: str, entry_files: list[dict[str, Any]], modules: list[dict[str, Any]]) -> list[str]:
    priority_names = ["AGENTS.md", "README.md", "SKILL.md", "registry.json", "entry_contract.json", "workflow.lgwf"]
    ordered: list[str] = []
    for name in priority_names:
        ordered.extend(item["path"] for item in entry_files if item["path"].endswith(name))

    if focus == "workflow-authoring":
        ordered.extend(module["path"] for module in modules if "workflow" in module["kind"])
    elif focus == "handoff":
        ordered.extend(item["path"] for item in entry_files if item["path"].endswith(("AGENTS.md", "README.md")))
    elif focus == "review":
        ordered.extend(module["path"] for module in modules if module.get("tests"))
    else:
        ordered.extend(module["path"] for module in modules[:20])

    deduped: list[str] = []
    seen: set[str] = set()
    for item in ordered:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped[:60]


def write_markdown(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def render_repo_context_pack(
    target_dir: Path,
    focus: str,
    depth: str,
    entry_files: list[dict[str, Any]],
    modules: list[dict[str, Any]],
    commands: list[dict[str, Any]],
    risks: list[dict[str, Any]],
    read_order: list[str],
) -> list[str]:
    lines = [
        "# 仓库上下文包",
        "",
        f"- 目标目录：`{target_dir}`",
        f"- 关注场景：`{focus}`",
        f"- 扫描深度：`{depth}`",
        f"- 生成时间：`{datetime.now(timezone.utc).isoformat()}`",
        "",
        "## 入口文件",
    ]
    if entry_files:
        lines.extend(f"- `{item['path']}`（{item['kind']}）" for item in entry_files[:80])
    else:
        lines.append("- 未发现常见入口文件。")

    lines.extend(["", "## 模块地图"])
    if modules:
        for module in modules[:80]:
            entries = ", ".join(f"`{item}`" for item in module["entry_files"]) or "无"
            lines.append(f"- `{module['path']}`：{module['kind']}；入口：{entries}")
    else:
        lines.append("- 未识别出明确模块。")

    lines.extend(["", "## 推荐阅读顺序"])
    if read_order:
        lines.extend(f"{index}. `{path}`" for index, path in enumerate(read_order, start=1))
    else:
        lines.append("- 从根目录 `README.md` 或 `AGENTS.md` 开始。")

    lines.extend(["", "## 命令清单摘要"])
    if commands:
        for item in commands[:40]:
            source = item["source"] if item["line"] is None else f"{item['source']}:{item['line']}"
            lines.append(f"- `{item['command']}`（来源：{source}）")
    else:
        lines.append("- 未从文档中识别出明确命令。")

    lines.extend(["", "## 风险和边界"])
    for risk in risks[:30]:
        source = risk["source"] if risk["line"] is None else f"{risk['source']}:{risk['line']}"
        lines.append(f"- {risk['text']}（来源：{source}）")
    return lines


def render_agent_handoff(
    target_dir: Path,
    focus: str,
    read_order: list[str],
    commands: list[dict[str, Any]],
    risks: list[dict[str, Any]],
) -> list[str]:
    lines = [
        "# Agent 交接摘要",
        "",
        f"目标目录：`{target_dir}`",
        f"关注场景：`{focus}`",
        "",
        "## 先读这些",
    ]
    lines.extend(f"- `{path}`" for path in read_order[:15]) if read_order else lines.append("- `AGENTS.md`、`README.md` 或最近任务相关入口。")
    lines.extend(["", "## 优先验证命令"])
    lines.extend(f"- `{item['command']}`" for item in commands[:10]) if commands else lines.append("- 当前上下文包未识别出验证命令。")
    lines.extend(["", "## 注意事项"])
    lines.extend(f"- {item['text']}" for item in risks[:12])
    return lines


def render_risk_register(risks: list[dict[str, Any]]) -> list[str]:
    lines = ["# 风险清单", ""]
    for index, risk in enumerate(risks, start=1):
        source = risk["source"] if risk["line"] is None else f"{risk['source']}:{risk['line']}"
        lines.append(f"{index}. {risk['text']}  ")
        lines.append(f"   来源：`{source}`")
    return lines


def render_read_order(read_order: list[str], focus: str) -> list[str]:
    lines = ["# 推荐阅读顺序", "", f"关注场景：`{focus}`", ""]
    if not read_order:
        lines.append("未识别出稳定阅读顺序；请从根目录入口文档开始。")
        return lines
    lines.extend(f"{index}. `{path}`" for index, path in enumerate(read_order, start=1))
    return lines


def find_package_root(script_path: Path) -> Path:
    for candidate in [script_path.resolve(), *script_path.resolve().parents]:
        if (candidate / "scripts" / "build_context_pack.py").is_file() and (candidate / "wf").is_dir():
            return candidate
        if (candidate / "shared" / "scripts" / "repo_context_runtime.py").is_file():
            return candidate
    return script_path.resolve().parents[2]


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
    target_dir = Path(request["target_dir"]).resolve()
    dirs, files = walk_target(target_dir, request["depth"], int(request["max_files"]))
    entry_files = detect_entry_files(target_dir, files)
    modules = detect_modules(target_dir, dirs)
    commands = extract_commands(target_dir, files)
    risks = extract_risks(target_dir, files)
    read_order = build_read_order(request["focus"], entry_files, modules)
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
    args = argparse.Namespace(
        target_dir=request["target_dir"],
        output_dir=request["output_dir"],
        focus=request["focus"],
        depth=request["depth"],
        max_files=int(request["max_files"]),
    )
    target_dir = Path(args.target_dir).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    dirs, files = walk_target(target_dir, args.depth, args.max_files)
    entry_files = detect_entry_files(target_dir, files)
    modules = detect_modules(target_dir, dirs)
    commands = extract_commands(target_dir, files)
    risks = extract_risks(target_dir, files)
    read_order = build_read_order(args.focus, entry_files, modules)

    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "module_map.json", {"target_dir": str(target_dir), "modules": modules})
    write_json(output_dir / "command_inventory.json", {"target_dir": str(target_dir), "commands": commands})
    write_markdown(
        output_dir / "repo_context_pack.md",
        render_repo_context_pack(target_dir, args.focus, args.depth, entry_files, modules, commands, risks, read_order),
    )
    write_markdown(output_dir / "agent_handoff.md", render_agent_handoff(target_dir, args.focus, read_order, commands, risks))
    write_markdown(output_dir / "risk_register.md", render_risk_register(risks))
    write_markdown(output_dir / "read_order.md", render_read_order(read_order, args.focus))

    summary = {
        "target_dir": str(target_dir),
        "output_dir": str(output_dir),
        "focus": args.focus,
        "depth": args.depth,
        "scanned_file_count": len(files),
        "module_count": len(modules),
        "command_count": len(commands),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "artifacts": ARTIFACT_NAMES,
        "runtime_root": str(package_root),
    }
    write_json(output_dir / "summary.json", summary)
    return summary


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
