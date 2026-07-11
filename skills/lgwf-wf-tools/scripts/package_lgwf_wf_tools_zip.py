from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import zipfile


DEFAULT_ZIP_NAME = "lgwf-wf-tools.zip"
DEFAULT_EXCLUDED_NAMES = {
    ".git",
    ".lgwf",
    ".local",
    ".mypy_cache",
    ".pytest_cache",
    "__pycache__",
    "output",
}
DEFAULT_EXCLUDED_SUFFIXES = {".pyc", ".pyo"}
REQUIRED_SOURCE_FILES = ("SKILL.md", "AGENTS.md", "README.md", "registry.json")


@dataclass(frozen=True)
class FacadeZipResult:
    source_root: Path
    output_zip: Path
    included_file_count: int
    excluded_names: tuple[str, ...]
    excluded_suffixes: tuple[str, ...]


def default_source_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_output_zip() -> Path:
    return default_source_root() / "output" / DEFAULT_ZIP_NAME


def _validate_source_root(source_root: Path) -> None:
    for filename in REQUIRED_SOURCE_FILES:
        path = source_root / filename
        if not path.is_file():
            raise FileNotFoundError(f"source root missing required file: {filename}")


def _iter_included_files(source_root: Path, output_zip: Path) -> list[Path]:
    output_zip = output_zip.resolve()
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(source_root):
        dirnames[:] = sorted(name for name in dirnames if name not in DEFAULT_EXCLUDED_NAMES)
        current_dir = Path(dirpath)
        for filename in sorted(filenames):
            path = current_dir / filename
            if filename in DEFAULT_EXCLUDED_NAMES:
                continue
            if path.suffix in DEFAULT_EXCLUDED_SUFFIXES:
                continue
            if path.resolve() == output_zip:
                continue
            files.append(path)
    return files


def package_facade_zip(
    *,
    source_root: Path | None = None,
    output_zip: Path | None = None,
    force: bool = True,
) -> FacadeZipResult:
    source_root = (source_root or default_source_root()).resolve()
    output_zip = (output_zip or default_output_zip()).resolve()

    _validate_source_root(source_root)
    if output_zip.suffix.lower() != ".zip":
        raise ValueError(f"output path must end with .zip: {output_zip}")
    if output_zip.exists():
        if not force:
            raise FileExistsError(f"output zip already exists: {output_zip}")
        output_zip.unlink()

    output_zip.parent.mkdir(parents=True, exist_ok=True)
    included_files = _iter_included_files(source_root, output_zip)
    with zipfile.ZipFile(output_zip, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in included_files:
            relative_path = path.relative_to(source_root)
            archive.write(path, Path(source_root.name) / relative_path)

    return FacadeZipResult(
        source_root=source_root,
        output_zip=output_zip,
        included_file_count=len(included_files),
        excluded_names=tuple(sorted(DEFAULT_EXCLUDED_NAMES)),
        excluded_suffixes=tuple(sorted(DEFAULT_EXCLUDED_SUFFIXES)),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="将 lgwf-wf-tools skill 打包为 zip，默认输出到 output/ 并排除本地状态目录。"
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        default=default_source_root(),
        help="源 lgwf-wf-tools 目录；默认使用脚本所在 skill 根目录。",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=default_output_zip(),
        help="输出 zip 路径；默认写入 lgwf-wf-tools/output/lgwf-wf-tools.zip。",
    )
    force_group = parser.add_mutually_exclusive_group()
    force_group.add_argument("--force", dest="force", action="store_true", help="覆盖已存在的 zip（默认）。")
    force_group.add_argument("--no-force", dest="force", action="store_false", help="输出 zip 已存在时直接失败。")
    parser.set_defaults(force=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = package_facade_zip(source_root=args.source_root, output_zip=args.output, force=args.force)
    print(
        json.dumps(
            {
                "source_root": str(result.source_root),
                "output_zip": str(result.output_zip),
                "included_file_count": result.included_file_count,
                "excluded_names": list(result.excluded_names),
                "excluded_suffixes": list(result.excluded_suffixes),
                "force": args.force,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
