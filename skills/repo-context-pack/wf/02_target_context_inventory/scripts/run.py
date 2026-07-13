"""生成 repo-context-pack 第二阶段的目标资料清点结果。"""

from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

OUTPUT_ARTIFACT = Path(".lgwf") / "context_inventory.json"

IGNORED_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    ".lgwf",
    ".idea",
    ".vscode",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
}
TEXT_EXTENSIONS = {
    ".md",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".py",
    ".ps1",
    ".sh",
    ".bash",
    ".zsh",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".java",
    ".go",
    ".rs",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".env",
    ".properties",
    ".sql",
    ".xml",
    ".html",
    ".css",
    ".scss",
    ".prompt",
    ".lgwf",
}
ENTRYPOINT_FILES = {
    "readme.md": "仓库说明入口",
    "agents.md": "协作规则入口",
    "skill.md": "skill 入口",
    "workflow.lgwf": "workflow 入口",
    "entry_contract.json": "workflow 输入契约",
    "package.json": "Node package 入口",
    "pyproject.toml": "Python package 配置",
    "setup.py": "Python setup 入口",
    "requirements.txt": "Python 依赖清单",
    "main.py": "Python 主入口候选",
    "app.py": "应用入口候选",
    "cli.py": "CLI 入口候选",
    "index.js": "JavaScript 入口候选",
    "index.ts": "TypeScript 入口候选",
}
MODULE_SIGNALS = {
    "workflow.lgwf": "lgwf_workflow_package",
    "entry_contract.json": "lgwf_workflow_package",
    "SKILL.md": "codex_skill",
    "package.json": "node_package",
    "pyproject.toml": "python_package",
    "requirements.txt": "python_package",
    "Cargo.toml": "rust_package",
    "go.mod": "go_package",
}
COMMAND_PREFIXES = (
    "python ",
    "py ",
    "pytest ",
    "uv ",
    "pip ",
    "npm ",
    "pnpm ",
    "yarn ",
    "node ",
    "pwsh ",
    "powershell ",
    "bash ",
    "sh ",
    "make ",
    "just ",
    "cargo ",
    "go ",
    "dotnet ",
    "java ",
    "poetry ",
)
SHELL_BLOCK_LANGS = {"bash", "sh", "shell", "powershell", "pwsh", "cmd"}
RISK_PATTERN = re.compile(r"\b(TODO|FIXME|HACK|XXX|TBD)\b|待办|风险|阻塞|缺失|手工处理", re.IGNORECASE)
ABSOLUTE_PATH_DRIVE_PATTERN = re.compile(r"^[A-Za-z]:[\\/]")
MAX_TARGETS = 128
MAX_FILES = 400
MAX_FILE_BYTES = 128 * 1024
MAX_LINES = 200
MAX_COMMANDS = 200
MAX_RISK_MARKERS = 200
MAX_FILE_RECORDS = 400
MAX_ENTRYPOINTS = 80
MAX_MODULES = 80


def load_json(path: Path) -> Any:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_stdin_payload() -> dict[str, Any]:
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    parsed = json.loads(raw)
    return parsed if isinstance(parsed, dict) else {}


def nested_lookup(payload: dict[str, Any], dotted_key: str) -> Any:
    current: Any = payload
    for part in dotted_key.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        cleaned = value.strip()
        return [cleaned] if cleaned else []
    if isinstance(value, (list, tuple, set)):
        result: list[str] = []
        for item in value:
            cleaned = str(item).strip()
            if cleaned:
                result.append(cleaned)
        return result
    cleaned = str(value).strip()
    return [cleaned] if cleaned else []


def unique_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def collect_targets(payloads: list[dict[str, Any]], kind: str) -> list[str]:
    if kind == "dir":
        plural_keys = [
            "target_dirs",
            "target_directories",
            "analysis_target_dirs",
            "normalized_target_dirs",
            "targets.dirs",
            "scope.target_dirs",
            "request.target_dirs",
            "request.targets.dirs",
        ]
        singular_keys = ["target_dir", "analysis_target_dir", "scope.target_dir", "request.target_dir"]
    else:
        plural_keys = [
            "target_files",
            "analysis_target_files",
            "normalized_target_files",
            "targets.files",
            "scope.target_files",
            "request.target_files",
            "request.targets.files",
        ]
        singular_keys = ["target_file", "analysis_target_file", "scope.target_file", "request.target_file"]

    collected: list[str] = []
    for payload in payloads:
        for key in plural_keys:
            collected.extend(string_list(nested_lookup(payload, key)))
        for key in singular_keys:
            collected.extend(string_list(nested_lookup(payload, key)))
    return unique_strings(collected[:MAX_TARGETS])


def workspace_relative(path: Path, workspace_root: Path) -> str | None:
    try:
        return path.resolve().relative_to(workspace_root.resolve()).as_posix()
    except ValueError:
        return None


def resolve_target(path_text: str, workspace_root: Path) -> Path:
    raw = Path(path_text)
    if raw.is_absolute() or ABSOLUTE_PATH_DRIVE_PATTERN.match(path_text):
        return raw.resolve()
    return (workspace_root / raw).resolve()


def target_record(path_text: str, kind: str, workspace_root: Path) -> dict[str, Any]:
    resolved = resolve_target(path_text, workspace_root)
    exists = resolved.exists()
    relative = workspace_relative(resolved, workspace_root)
    actual_kind = "missing"
    if exists and resolved.is_dir():
        actual_kind = "dir"
    elif exists and resolved.is_file():
        actual_kind = "file"
    return {
        "requested_path": path_text.replace("\\", "/"),
        "resolved_path": resolved.as_posix(),
        "workspace_relative": relative,
        "expected_kind": kind,
        "actual_kind": actual_kind,
        "exists": exists,
        "outside_workspace": relative is None,
    }


def detect_binary(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            sample = handle.read(2048)
    except OSError:
        return True
    return b"\x00" in sample


def read_text_sample(path: Path) -> tuple[str, bool, int]:
    try:
        size_bytes = path.stat().st_size
        with path.open("rb") as handle:
            raw = handle.read(MAX_FILE_BYTES + 1)
    except OSError:
        return "", True, 0
    truncated = size_bytes > MAX_FILE_BYTES or len(raw) > MAX_FILE_BYTES
    snippet = raw[:MAX_FILE_BYTES]
    text = snippet.decode("utf-8", errors="replace")
    lines = text.splitlines()
    line_truncated = len(lines) > MAX_LINES
    if line_truncated:
        lines = lines[:MAX_LINES]
    return "\n".join(lines), truncated or line_truncated, size_bytes


def is_text_candidate(path: Path) -> bool:
    suffix = path.suffix.lower()
    return suffix in TEXT_EXTENSIONS or path.name in {"README", "README.md", "AGENTS.md", "SKILL.md"}


def normalized_file_path(path: Path, workspace_root: Path) -> str:
    rel = workspace_relative(path, workspace_root)
    return rel if rel is not None else path.as_posix()


class InventoryCollector:
    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root.resolve()
        self.files: list[dict[str, Any]] = []
        self.entrypoints: list[dict[str, Any]] = []
        self.modules: list[dict[str, Any]] = []
        self.commands: list[dict[str, Any]] = []
        self.risk_markers: list[dict[str, Any]] = []
        self.extension_counts: Counter[str] = Counter()
        self.entrypoint_seen: set[str] = set()
        self.module_seen: set[str] = set()
        self.command_seen: set[tuple[str, int, str]] = set()
        self.risk_seen: set[tuple[str, int, str]] = set()
        self.total_scanned_dirs = 0
        self.total_scanned_files = 0
        self.total_sampled_text_files = 0
        self.truncation = {
            "file_limit_reached": False,
            "skipped_binary_files": [],
            "truncated_files": [],
            "skipped_directories": [],
            "missing_targets": [],
        }

    def add_missing_target(self, record: dict[str, Any]) -> None:
        self.truncation["missing_targets"].append(record)

    def register_module(self, directory: Path, signals: list[str]) -> None:
        if len(self.modules) >= MAX_MODULES:
            return
        key = directory.as_posix()
        if key in self.module_seen:
            return
        self.module_seen.add(key)
        module_type = "generic_module"
        for signal in signals:
            module_type = MODULE_SIGNALS.get(signal, module_type)
            if module_type != "generic_module":
                break
        self.modules.append(
            {
                "root": normalized_file_path(directory, self.workspace_root),
                "module_type": module_type,
                "signals": signals,
            }
        )

    def register_entrypoint(self, path: Path, reason: str) -> None:
        if len(self.entrypoints) >= MAX_ENTRYPOINTS:
            return
        normalized = normalized_file_path(path, self.workspace_root)
        if normalized in self.entrypoint_seen:
            return
        self.entrypoint_seen.add(normalized)
        self.entrypoints.append({"path": normalized, "reason": reason})

    def register_command(self, source: str, line_number: int, command: str, origin: str) -> None:
        if len(self.commands) >= MAX_COMMANDS:
            return
        key = (source, line_number, command)
        if key in self.command_seen:
            return
        self.command_seen.add(key)
        self.commands.append(
            {
                "source": source,
                "line": line_number,
                "command": command,
                "origin": origin,
            }
        )

    def register_risk(self, source: str, line_number: int, marker: str, excerpt: str) -> None:
        if len(self.risk_markers) >= MAX_RISK_MARKERS:
            return
        key = (source, line_number, marker)
        if key in self.risk_seen:
            return
        self.risk_seen.add(key)
        self.risk_markers.append(
            {
                "source": source,
                "line": line_number,
                "marker": marker,
                "excerpt": excerpt[:200],
            }
        )

    def scan_directory(self, target: dict[str, Any]) -> None:
        directory = Path(target["resolved_path"])
        if not directory.exists():
            self.add_missing_target(target)
            return
        if not directory.is_dir():
            self.add_missing_target(target)
            return

        for root, dirs, files in os.walk(directory):
            root_path = Path(root)
            self.total_scanned_dirs += 1
            filtered_dirs = []
            for name in sorted(dirs):
                if name in IGNORED_DIR_NAMES:
                    self.truncation["skipped_directories"].append(
                        normalized_file_path(root_path / name, self.workspace_root)
                    )
                    continue
                filtered_dirs.append(name)
            dirs[:] = filtered_dirs

            manifest_signals = [name for name in sorted(files) if name in MODULE_SIGNALS]
            if manifest_signals:
                self.register_module(root_path, manifest_signals)

            for file_name in sorted(files):
                if self.total_scanned_files >= MAX_FILES:
                    self.truncation["file_limit_reached"] = True
                    return
                self.scan_file(root_path / file_name, origin="dir_target")

    def scan_explicit_file(self, target: dict[str, Any]) -> None:
        path = Path(target["resolved_path"])
        if not path.exists() or not path.is_file():
            self.add_missing_target(target)
            return
        self.scan_file(path, origin="file_target")

    def scan_file(self, path: Path, origin: str) -> None:
        self.total_scanned_files += 1
        normalized = normalized_file_path(path, self.workspace_root)
        size_bytes = path.stat().st_size if path.exists() else 0
        extension = path.suffix.lower() or "<no_ext>"
        self.extension_counts[extension] += 1

        entry_reason = ENTRYPOINT_FILES.get(path.name.lower())
        if entry_reason:
            self.register_entrypoint(path, entry_reason)
        if path.name == "workflow.lgwf" and "wf" in path.parts:
            self.register_entrypoint(path, "workflow 编排入口")
        if path.name in MODULE_SIGNALS:
            self.register_module(path.parent, [path.name])

        file_record: dict[str, Any] = {
            "path": normalized,
            "origin": origin,
            "size_bytes": size_bytes,
            "extension": extension,
            "text_sampled": False,
            "truncated": False,
            "command_count": 0,
            "risk_marker_count": 0,
        }

        if not is_text_candidate(path) or detect_binary(path):
            self.truncation["skipped_binary_files"].append(normalized)
            if len(self.files) < MAX_FILE_RECORDS:
                self.files.append(file_record)
            return

        text, truncated, original_size = read_text_sample(path)
        file_record["text_sampled"] = True
        file_record["truncated"] = truncated
        file_record["size_bytes"] = original_size
        self.total_sampled_text_files += 1
        if truncated:
            self.truncation["truncated_files"].append(normalized)

        command_count, risk_count = self.extract_text_insights(normalized, text)
        file_record["command_count"] = command_count
        file_record["risk_marker_count"] = risk_count
        if len(self.files) < MAX_FILE_RECORDS:
            self.files.append(file_record)

    def extract_text_insights(self, source: str, text: str) -> tuple[int, int]:
        command_count = 0
        risk_count = 0
        in_shell_block = False
        shell_block_lang = ""

        for index, raw_line in enumerate(text.splitlines(), start=1):
            line = raw_line.rstrip()
            stripped = line.strip()

            if stripped.startswith("```"):
                fence_lang = stripped[3:].strip().lower()
                if in_shell_block:
                    in_shell_block = False
                    shell_block_lang = ""
                elif fence_lang in SHELL_BLOCK_LANGS:
                    in_shell_block = True
                    shell_block_lang = fence_lang
                continue

            if in_shell_block and stripped and not stripped.startswith("#"):
                self.register_command(source, index, stripped, f"fenced:{shell_block_lang}")
                command_count += 1

            prompt_match = re.match(r"^\s*(?:\$|PS>|>)\s*(.+)$", line)
            if prompt_match:
                command = prompt_match.group(1).strip()
                if command:
                    self.register_command(source, index, command, "prompt_line")
                    command_count += 1
            else:
                lowered = stripped.lower()
                if any(lowered.startswith(prefix) for prefix in COMMAND_PREFIXES):
                    self.register_command(source, index, stripped, "inline")
                    command_count += 1

            risk_match = RISK_PATTERN.search(line)
            if risk_match:
                marker = risk_match.group(0)
                self.register_risk(source, index, marker, stripped or line)
                risk_count += 1

        return command_count, risk_count

    def build_summary(self, targets: list[dict[str, Any]]) -> dict[str, Any]:
        existing_targets = sum(1 for item in targets if item["exists"])
        return {
            "requested_targets": len(targets),
            "existing_targets": existing_targets,
            "scanned_dirs": self.total_scanned_dirs,
            "scanned_files": self.total_scanned_files,
            "sampled_text_files": self.total_sampled_text_files,
            "modules_detected": len(self.modules),
            "entrypoints_detected": len(self.entrypoints),
            "commands_detected": len(self.commands),
            "risk_markers_detected": len(self.risk_markers),
            "top_extensions": dict(self.extension_counts.most_common(12)),
        }


def build_inventory(stdin_payload: dict[str, Any]) -> dict[str, Any]:
    workspace_root = Path.cwd().resolve()
    payloads = [stdin_payload]
    dir_targets = [target_record(item, "dir", workspace_root) for item in collect_targets(payloads, "dir")]
    file_targets = [target_record(item, "file", workspace_root) for item in collect_targets(payloads, "file")]
    collector = InventoryCollector(workspace_root)

    if not dir_targets and not file_targets:
        collector.truncation["missing_targets"].append(
            {
                "requested_path": "",
                "resolved_path": "",
                "workspace_relative": None,
                "expected_kind": "dir_or_file",
                "actual_kind": "missing",
                "exists": False,
                "outside_workspace": False,
                "reason": "上一阶段未提供 target_dirs 或 target_files",
            }
        )

    for target in dir_targets:
        collector.scan_directory(target)
    for target in file_targets:
        if collector.total_scanned_files >= MAX_FILES:
            collector.truncation["file_limit_reached"] = True
            break
        collector.scan_explicit_file(target)

    all_targets = dir_targets + file_targets
    inventory = {
        "stage_id": "target_context_inventory",
        "artifact": {
            "path": OUTPUT_ARTIFACT.as_posix(),
            "producer": "wf/02_target_context_inventory/scripts/run.py",
            "consumer_stage": "03_context_pack_rendering",
        },
        "request_source": {
            "stdin_keys": sorted(stdin_payload.keys()),
            "expected_request_artifact": ".lgwf/repo_context_pack_request.json",
            "loaded_request_artifact": False,
            "effective_target_dirs": [item["requested_path"] for item in dir_targets],
            "effective_target_files": [item["requested_path"] for item in file_targets],
        },
        "scan_policy": {
            "mode": "deterministic_python",
            "execution": "never_execute_discovered_commands",
            "ignored_dir_names": sorted(IGNORED_DIR_NAMES),
            "max_targets": MAX_TARGETS,
            "max_files": MAX_FILES,
            "max_file_bytes": MAX_FILE_BYTES,
            "max_lines_per_file": MAX_LINES,
            "max_commands": MAX_COMMANDS,
            "max_risk_markers": MAX_RISK_MARKERS,
        },
        "inventory": {
            "targets": all_targets,
            "summary": collector.build_summary(all_targets),
            "files": collector.files,
            "entrypoints": collector.entrypoints,
            "modules": collector.modules,
            "commands": collector.commands,
            "risk_markers": collector.risk_markers,
            "truncation": collector.truncation,
        },
        "notes": [
            "本阶段只做确定性 Python 清点，不调用运行时 Codex prompt 扫描目标仓库。",
            "提取出的命令、测试命令、TODO 和修复步骤仅作为上下文，不会在本阶段执行。",
            "若上一阶段未提供目标范围，本结果会保留空清单并把缺失目标记入 truncation.missing_targets。",
        ],
    }
    return inventory


def verify_inventory_artifact(stdin_payload: dict[str, Any]) -> dict[str, Any]:
    inventory = load_json(OUTPUT_ARTIFACT)
    artifact_path = ""
    if isinstance(inventory, dict):
        artifact = inventory.get("artifact")
        if isinstance(artifact, dict):
            artifact_path = str(artifact.get("path", "")).strip()
    summary = {}
    if isinstance(inventory, dict):
        inventory_section = inventory.get("inventory")
        if isinstance(inventory_section, dict):
            maybe_summary = inventory_section.get("summary")
            if isinstance(maybe_summary, dict):
                summary = maybe_summary
    return {
        "verified": artifact_path == OUTPUT_ARTIFACT.as_posix(),
        "artifact_path": OUTPUT_ARTIFACT.as_posix(),
        "input_stage_id": stdin_payload.get("stage_id"),
        "scanned_files": summary.get("scanned_files", 0),
        "commands_detected": summary.get("commands_detected", 0),
        "risk_markers_detected": summary.get("risk_markers_detected", 0),
    }


def main() -> None:
    stdin_payload = read_stdin_payload()
    if stdin_payload.get("stage_id") == "target_context_inventory":
        verification = verify_inventory_artifact(stdin_payload)
        print(
            json.dumps(
                {
                    "repo_context_pack.context_inventory_verification": verification,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    request_payload = stdin_payload if isinstance(stdin_payload, dict) else {}
    inventory = build_inventory(request_payload)
    write_json(OUTPUT_ARTIFACT, inventory)
    print(json.dumps({"repo_context_pack.context_inventory": inventory}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
