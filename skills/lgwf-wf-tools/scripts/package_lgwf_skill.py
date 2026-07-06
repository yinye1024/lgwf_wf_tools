from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


PACKAGER_NAME = "lgwf-wf-tools/skill-packaging"
DEFAULT_EXCLUDED_NAMES = {
    ".git",
    ".lgwf",
    ".local",
    ".mypy_cache",
    ".pytest_cache",
    "__pycache__",
    "reports",
    "ws",
}
DEFAULT_EXCLUDED_SUFFIXES = {".pyc", ".pyo"}


@dataclass(frozen=True)
class PackageResult:
    output_skill: Path
    manifest_path: Path


def _copy_tree_filtered(source: Path, target: Path) -> None:
    def ignore(_dir: str, names: list[str]) -> set[str]:
        ignored: set[str] = set()
        for name in names:
            if name in DEFAULT_EXCLUDED_NAMES or Path(name).suffix in DEFAULT_EXCLUDED_SUFFIXES:
                ignored.add(name)
        return ignored

    shutil.copytree(source, target, ignore=ignore)


def _validate_source_skill(source_skill: Path) -> None:
    required = [
        source_skill / "SKILL.md",
        source_skill / "AGENTS.md",
        source_skill / "README.md",
        source_skill / "wf" / "workflow.lgwf",
    ]
    for path in required:
        if not path.is_file():
            relative = path.relative_to(source_skill).as_posix()
            raise FileNotFoundError(f"source skill missing required file: {relative}")


def _validate_runtime(runtime_source: Path) -> None:
    required = [
        runtime_source / "AGENTS.md",
        runtime_source / "scripts" / "lgwf.py",
    ]
    for path in required:
        if not path.is_file():
            relative = path.relative_to(runtime_source).as_posix()
            raise FileNotFoundError(f"lgwf-client-assist runtime missing required file: {relative}")


def _write_local_runner(output_skill: Path) -> Path:
    scripts_dir = output_skill / "scripts"
    scripts_dir.mkdir(exist_ok=True)
    runner = scripts_dir / "run_local_lgwf_workflow.py"
    runner.write_text(
        '''from __future__ import annotations

import subprocess
import sys
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
LGWF_PY = SKILL_ROOT / "vendor" / "lgwf-client-assist" / "scripts" / "lgwf.py"


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    command = [
        sys.executable,
        str(LGWF_PY),
        "run",
        "--workflow-lgwf",
        "wf/workflow.lgwf",
        "--work-dir",
        "ws",
        *args,
    ]
    completed = subprocess.run(command, cwd=str(SKILL_ROOT))
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
''',
        encoding="utf-8",
    )
    return runner


def _write_manifest(source_skill: Path, output_skill: Path, runtime_source: Path) -> Path:
    manifest = {
        "packager": PACKAGER_NAME,
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source_skill_name": source_skill.name,
        "source_skill_path": str(source_skill.resolve()),
        "runtime_source_path": str(runtime_source.resolve()),
        "runtime_relative_path": "vendor/lgwf-client-assist",
        "local_runner": "scripts/run_local_lgwf_workflow.py",
        "excluded_names": sorted(DEFAULT_EXCLUDED_NAMES),
        "excluded_suffixes": sorted(DEFAULT_EXCLUDED_SUFFIXES),
    }
    manifest_path = output_skill / "PACKAGING_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest_path


def package_skill(
    source_skill: Path,
    output_parent: Path,
    runtime_source: Path,
    force: bool = False,
) -> PackageResult:
    source_skill = source_skill.resolve()
    output_parent = output_parent.resolve()
    runtime_source = runtime_source.resolve()
    output_skill = output_parent / source_skill.name

    _validate_source_skill(source_skill)
    _validate_runtime(runtime_source)

    if output_skill.exists():
        if not force:
            raise FileExistsError(f"output skill already exists: {output_skill}")
        shutil.rmtree(output_skill)

    output_parent.mkdir(parents=True, exist_ok=True)
    _copy_tree_filtered(source_skill, output_skill)

    runtime_target = output_skill / "vendor" / "lgwf-client-assist"
    runtime_target.parent.mkdir(parents=True, exist_ok=True)
    _copy_tree_filtered(runtime_source, runtime_target)

    _write_local_runner(output_skill)
    manifest_path = _write_manifest(source_skill, output_skill, runtime_source)
    return PackageResult(output_skill=output_skill, manifest_path=manifest_path)


def _default_runtime_source() -> Path:
    return Path(__file__).resolve().parents[1] / "vendor" / "lgwf-client-assist"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="把带 wf/workflow.lgwf 的 LGWF workflow skill 打包为自包含 skill。"
    )
    parser.add_argument("--source-skill", required=True, type=Path, help="源 skill 目录。")
    parser.add_argument("--output-parent", required=True, type=Path, help="输出父目录。")
    parser.add_argument(
        "--runtime-source",
        type=Path,
        default=_default_runtime_source(),
        help="lgwf-client-assist runtime 目录；默认使用同仓库 lgwf-wf-tools vendor。",
    )
    parser.add_argument("--force", action="store_true", help="覆盖已存在的输出目录。")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = package_skill(
        source_skill=args.source_skill,
        output_parent=args.output_parent,
        runtime_source=args.runtime_source,
        force=args.force,
    )
    print(
        json.dumps(
            {
                "output_skill": str(result.output_skill),
                "manifest_path": str(result.manifest_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
