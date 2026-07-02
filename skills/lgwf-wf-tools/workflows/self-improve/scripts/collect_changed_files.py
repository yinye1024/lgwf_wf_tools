from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


from _paths import FACADE_ROOT, SELF_IMPROVE_ROOT


def repo_root_for(path: Path) -> Path:
    completed = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--show-toplevel"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return Path(completed.stdout.strip()).resolve()


def git_changed_files(repo_root: Path) -> list[Path]:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), "status", "--porcelain=v1", "--untracked-files=all"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    paths: list[Path] = []
    for line in completed.stdout.splitlines():
        if not line:
            continue
        raw_path = line[3:]
        if " -> " in raw_path:
            raw_path = raw_path.split(" -> ", 1)[1]
        paths.append((repo_root / raw_path).resolve())
    return paths


def relative_to_facade(paths: list[Path]) -> list[str]:
    relative: list[str] = []
    facade = FACADE_ROOT.resolve()
    for path in paths:
        try:
            relative.append(path.relative_to(facade).as_posix())
        except ValueError:
            continue
    return sorted(set(relative))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    repo_root = repo_root_for(FACADE_ROOT)
    changed = relative_to_facade(git_changed_files(repo_root))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(changed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "count": len(changed)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
