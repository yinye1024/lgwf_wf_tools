from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


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

FOCUS_VALUES = {"onboarding", "modification", "review", "workflow-authoring", "handoff"}
DEPTH_TO_MAX_DEPTH = {"light": 2, "normal": 4, "deep": 8}

COMMAND_RE = re.compile(
    r"^\s*(?:PS>\s*|\$\s*)?"
    r"(?P<cmd>(?:python|py|pytest|ruff|mypy|npm|pnpm|yarn|uv|git|node|npx|docker|make|pwsh|powershell)\b.+|(?:\.{0,2}[\\/])?[\w./\\:-]*lgwf\.py\b.+)",
    re.IGNORECASE,
)
RISK_RE = re.compile(r"(禁止|不得|不要|必须|只允许|状态边界|UTF-8|no BOM|approval|vendor|\.lgwf|work_dir|work dir)")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate an AI-agent context pack for a repository.")
    parser.add_argument("--target-dir", required=True, help="要分析的仓库或模块目录。")
    parser.add_argument("--output-dir", required=True, help="上下文包输出目录。")
    parser.add_argument("--focus", choices=sorted(FOCUS_VALUES), default="onboarding")
    parser.add_argument("--depth", choices=sorted(DEPTH_TO_MAX_DEPTH), default="normal")
    parser.add_argument("--max-files", type=int, default=1600, help="最多扫描的文件数量。")
    return parser.parse_args(argv)


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
        tests_path = "tests" if (directory / "tests").exists() else None
        modules.append(
            {
                "path": module_path,
                "kind": kind,
                "entry_files": sorted(set(entry_files)),
                "has_agents_md": (directory / "AGENTS.md").exists(),
                "has_readme": (directory / "README.md").exists(),
                "tests": tests_path,
            }
        )
    return modules


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
            key = command.lower()
            commands.setdefault(
                key,
                {"command": command, "source": rel(path, root), "line": line_number, "inferred": False},
            )

    inferred = infer_commands(root)
    for item in inferred:
        commands.setdefault(item["command"].lower(), item)
    return sorted(commands.values(), key=lambda item: (item.get("inferred", False), item["source"], item["command"]))


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


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_markdown(path: Path, lines: list[str]) -> None:
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


def render_agent_handoff(target_dir: Path, focus: str, read_order: list[str], commands: list[dict[str, Any]], risks: list[dict[str, Any]]) -> list[str]:
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


def build_pack(args: argparse.Namespace) -> dict[str, Any]:
    target_dir = Path(args.target_dir).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    if not target_dir.exists() or not target_dir.is_dir():
        raise SystemExit(f"target_dir does not exist or is not a directory: {target_dir}")

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
        "artifacts": [
            "repo_context_pack.md",
            "agent_handoff.md",
            "module_map.json",
            "command_inventory.json",
            "risk_register.md",
            "read_order.md",
            "summary.json",
        ],
    }
    write_json(output_dir / "summary.json", summary)
    return summary


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    summary = build_pack(args)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
