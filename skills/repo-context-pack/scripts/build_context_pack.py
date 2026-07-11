from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ARTIFACT_NAMES = [
    "repo_context_pack.md",
    "agent_handoff.md",
    "module_map.json",
    "command_inventory.json",
    "risk_register.md",
    "read_order.md",
    "summary.json",
]

EXCLUDED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".lgwf",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "node_modules",
    "vendor",
    "ws",
}


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def relative(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def walk_target(target_dir: Path, depth: str, max_files: int) -> tuple[list[str], list[str]]:
    depth_limit = {"light": 2, "normal": 4, "deep": 8}.get(depth, 4)
    dirs: list[str] = []
    files: list[str] = []
    for current, dir_names, file_names in target_dir.walk():
        current_path = Path(current)
        rel_parts = current_path.resolve().relative_to(target_dir.resolve()).parts
        dir_names[:] = [name for name in dir_names if name not in EXCLUDED_DIRS]
        if len(rel_parts) > depth_limit:
            dir_names[:] = []
            continue
        if rel_parts:
            dirs.append(relative(current_path, target_dir))
        for name in sorted(file_names):
            if len(files) >= max_files:
                break
            path = current_path / name
            if path.suffix.lower() in {".pyc", ".pyo", ".exe", ".dll", ".png", ".jpg", ".jpeg", ".gif", ".zip"}:
                continue
            files.append(relative(path, target_dir))
        if len(files) >= max_files:
            dir_names[:] = []
    return sorted(dirs), sorted(files)


def detect_entry_files(target_dir: Path, files: list[str]) -> list[str]:
    candidates = []
    priority_names = {"README.md", "AGENTS.md", "SKILL.md", "pyproject.toml", "package.json", "workflow.lgwf"}
    for path in files:
        name = Path(path).name
        if name in priority_names or path.endswith("/workflow.lgwf"):
            candidates.append(path)
    return candidates[:40]


def detect_modules(target_dir: Path, dirs: list[str]) -> list[dict[str, Any]]:
    modules: list[dict[str, Any]] = []
    for path in dirs:
        name = Path(path).name
        if name in {"tests", "scripts", "docs", "wf", "workflows", "skills"} or (target_dir / path / "__init__.py").is_file():
            modules.append({"path": path, "name": name, "kind": "directory"})
    return modules[:80]


def read_small(path: Path, limit: int = 200000) -> str:
    try:
        if path.stat().st_size > limit:
            return ""
        return path.read_text(encoding="utf-8-sig", errors="ignore")
    except OSError:
        return ""


def extract_commands(target_dir: Path, files: list[str]) -> list[dict[str, str]]:
    commands: list[dict[str, str]] = []
    command_pattern = re.compile(r"\b(python|pytest|npm|pnpm|yarn|uv|ruff|mypy|lgwf\.py)\b[^`\n]*")
    for rel_path in files:
        if Path(rel_path).suffix.lower() not in {".md", ".txt", ".toml", ".json", ".ps1", ".sh"}:
            continue
        text = read_small(target_dir / rel_path)
        for match in command_pattern.findall(text):
            line = next((line.strip(" `") for line in text.splitlines() if match in line), "")
            if line:
                commands.append({"source": rel_path, "command": line[:240]})
        if len(commands) >= 80:
            break
    return commands


def extract_risks(target_dir: Path, files: list[str]) -> list[str]:
    risks: list[str] = []
    markers = ("TODO", "FIXME", "HACK", "deprecated", "manual", "approval", "risk")
    for rel_path in files:
        if Path(rel_path).suffix.lower() not in {".md", ".py", ".lgwf", ".json", ".toml"}:
            continue
        text = read_small(target_dir / rel_path, 80000)
        if any(marker.lower() in text.lower() for marker in markers):
            risks.append(rel_path)
        if len(risks) >= 80:
            break
    return risks


def build_read_order(focus: str, entry_files: list[str], modules: list[dict[str, Any]]) -> list[str]:
    order = list(entry_files)
    order.extend(item["path"] for item in modules if item.get("path") not in order)
    return order[:80]


def render_markdown_pack(output_dir: Path, target_dir: Path, focus: str, modules: list[dict[str, Any]], commands: list[dict[str, str]], risks: list[str], read_order: list[str]) -> None:
    write_text(
        output_dir / "repo_context_pack.md",
        "\n".join([
            "# repo context pack",
            "",
            f"- 目标目录：`{target_dir}`",
            f"- focus：`{focus}`",
            "",
            "## 模块",
            *[f"- `{item['path']}`" for item in modules[:30]],
        ]),
    )
    write_text(
        output_dir / "agent_handoff.md",
        "\n".join(["# agent handoff", "", "## 推荐入口", *[f"- `{item}`" for item in read_order[:30]]]),
    )
    write_text(
        output_dir / "risk_register.md",
        "\n".join(["# risk register", "", *[f"- `{item}`" for item in risks[:60]]] or ["# risk register", "", "- 未发现明显风险标记"]),
    )
    write_text(
        output_dir / "read_order.md",
        "\n".join(["# read order", "", *[f"{index + 1}. `{item}`" for index, item in enumerate(read_order[:80])]]),
    )


def build_pack(args: argparse.Namespace) -> dict[str, Any]:
    target_dir = Path(args.target_dir).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    dirs, files = walk_target(target_dir, str(args.depth), int(args.max_files))
    entry_files = detect_entry_files(target_dir, files)
    modules = detect_modules(target_dir, dirs)
    commands = extract_commands(target_dir, files)
    risks = extract_risks(target_dir, files)
    read_order = build_read_order(str(args.focus), entry_files, modules)
    render_markdown_pack(output_dir, target_dir, str(args.focus), modules, commands, risks, read_order)
    write_json(output_dir / "module_map.json", {"target_dir": str(target_dir), "modules": modules, "entry_files": entry_files})
    write_json(output_dir / "command_inventory.json", {"commands": commands})
    summary = {
        "target_dir": str(target_dir),
        "output_dir": str(output_dir),
        "focus": str(args.focus),
        "depth": str(args.depth),
        "max_files": int(args.max_files),
        "scanned_file_count": len(files),
        "artifacts": ARTIFACT_NAMES,
    }
    write_json(output_dir / "summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a repo context pack.")
    parser.add_argument("--target-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--focus", default="onboarding")
    parser.add_argument("--depth", default="normal", choices=["light", "normal", "deep"])
    parser.add_argument("--max-files", type=int, default=1600)
    return parser.parse_args()


if __name__ == "__main__":
    print(json.dumps(build_pack(parse_args()), ensure_ascii=False, indent=2))
