from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "shared"))

from e2e_generator_common import LGWF_DIR, output_state, read_json, slugify, workflow_name_from_text, write_json


TEST_TYPE_ORDER = ("script_flow", "runtime_fake", "real_positive", "wf_fix_positive")


def relative_path_variants(path: Path) -> list[Path]:
    variants = [path]
    parts = path.parts
    if len(parts) >= 2 and parts[0] == "skills" and parts[1] == "lgwf-wf-tools":
        stripped = Path(*parts[2:])
        if stripped not in variants:
            variants.append(stripped)
    return variants


def resolve_path(raw: str, base: Path) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path.resolve()

    candidate_roots = [base]
    isolated_workspace = base.parent / "workspace"
    if isolated_workspace.is_dir():
        candidate_roots.append(isolated_workspace)

    candidates = [
        (root / relative).resolve()
        for root in candidate_roots
        for relative in relative_path_variants(path)
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def normalize_test_types(raw: object) -> list[str]:
    if raw is None or raw == []:
        return list(TEST_TYPE_ORDER)
    if not isinstance(raw, list):
        raise SystemExit("test_types must be an array of strings")
    values = []
    invalid = []
    for item in raw:
        if not isinstance(item, str):
            invalid.append(repr(item))
            continue
        value = item.strip()
        if value not in TEST_TYPE_ORDER:
            invalid.append(value)
        elif value not in values:
            values.append(value)
    if invalid:
        allowed = ", ".join(TEST_TYPE_ORDER)
        raise SystemExit(f"invalid test_types: {', '.join(invalid)}; allowed: {allowed}")
    if not values:
        return list(TEST_TYPE_ORDER)
    return [value for value in TEST_TYPE_ORDER if value in values]


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
    selected_test_types = normalize_test_types(request.get("test_types"))
    normalized = {
        "workflow_root": workflow_root.as_posix(),
        "workflow_lgwf": workflow_lgwf.as_posix(),
        "workflow_name": workflow_name,
        "test_output_dir": test_output_dir,
        "test_name_prefix": prefix,
        "selected_test_types": selected_test_types,
        "generated_tests": {
            "script_flow": f"test_{prefix}_script_flow_e2e.py",
            "runtime_fake": f"test_{prefix}_runtime_fake_e2e.py",
            "real_positive": f"lgwf_{prefix}_real_positive_e2e.py",
            "wf_fix_positive": f"lgwf_{prefix}_real_positive_e2e_for_wf_fix.py",
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
