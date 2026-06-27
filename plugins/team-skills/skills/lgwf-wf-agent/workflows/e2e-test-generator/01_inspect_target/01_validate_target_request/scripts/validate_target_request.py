from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "shared"))

from e2e_generator_common import LGWF_DIR, output_state, read_json, slugify, workflow_name_from_text, write_json


def resolve_path(raw: str, base: Path) -> Path:
    path = Path(raw)
    if not path.is_absolute():
        path = base / path
    return path.resolve()


def main() -> None:
    request_path = LGWF_DIR / "e2e_target_request.json"
    request = read_json(request_path)
    if not isinstance(request, dict):
        raise SystemExit("e2e target request must be a JSON object")

    cwd = Path.cwd()
    workflow_lgwf_raw = str(request.get("workflow_lgwf") or "").strip()
    if not workflow_lgwf_raw:
        raise SystemExit("workflow_lgwf is required")
    workflow_lgwf = resolve_path(workflow_lgwf_raw, cwd)
    if not workflow_lgwf.exists():
        raise SystemExit(f"workflow_lgwf does not exist: {workflow_lgwf}")
    if workflow_lgwf.name != "workflow.lgwf":
        raise SystemExit(f"workflow_lgwf must point to workflow.lgwf: {workflow_lgwf}")

    workflow_root = resolve_path(str(request.get("workflow_root") or workflow_lgwf.parent), cwd)
    if not workflow_root.exists() or not workflow_root.is_dir():
        raise SystemExit(f"workflow_root must be an existing directory: {workflow_root}")
    try:
        workflow_lgwf.relative_to(workflow_root)
    except ValueError as exc:
        raise SystemExit("workflow_lgwf must be inside workflow_root") from exc

    workflow_text = workflow_lgwf.read_text(encoding="utf-8")
    workflow_name = workflow_name_from_text(workflow_text) or workflow_lgwf.parent.name
    prefix = slugify(str(request.get("test_name_prefix") or workflow_name))
    test_output_dir = str(request.get("test_output_dir") or "tests").strip().replace("\\", "/").strip("/")
    if not test_output_dir or ".." in Path(test_output_dir).parts or Path(test_output_dir).is_absolute():
        raise SystemExit("test_output_dir must be a non-empty relative path without '..'")
    normalized = {
        "workflow_root": workflow_root.as_posix(),
        "workflow_lgwf": workflow_lgwf.as_posix(),
        "workflow_name": workflow_name,
        "test_output_dir": test_output_dir,
        "test_name_prefix": prefix,
        "generated_tests": {
            "script_flow": f"test_{prefix}_script_flow_e2e.py",
            "runtime_fake": f"test_{prefix}_runtime_fake_e2e.py",
            "real_positive": f"test_{prefix}_real_positive_e2e.py",
        },
    }
    write_json(LGWF_DIR / "e2e_target_request.normalized.json", normalized)
    output_state(
        {
            "target_request": normalized,
            "target_dirs": [workflow_root.as_posix()],
            "target_files": [workflow_lgwf.as_posix()],
            "test_output_dir": (workflow_root / test_output_dir).as_posix(),
        }
    )


if __name__ == "__main__":
    main()
