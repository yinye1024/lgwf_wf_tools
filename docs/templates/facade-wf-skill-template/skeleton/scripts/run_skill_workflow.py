from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


FACADE_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = FACADE_ROOT / "registry.json"


def _load_registry_workflow(workflow_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8-sig"))
    for workflow in registry.get("workflows", []):
        if workflow.get("id") != workflow_id:
            continue
        contract_path = FACADE_ROOT / workflow["entry_contract"]
        contract = json.loads(contract_path.read_text(encoding="utf-8-sig"))
        return workflow, contract
    raise ValueError(f"unknown workflow id: {workflow_id}")


def _pop_option(args: list[str], option: str) -> str | None:
    if option not in args:
        return None
    index = args.index(option)
    args.pop(index)
    if index >= len(args):
        raise ValueError(f"{option} requires a value")
    return args.pop(index)


def _pop_flag(args: list[str], option: str) -> bool:
    if option not in args:
        return False
    args.remove(option)
    return True


def _insert_option_if_missing(args: list[str], option: str, value: str) -> None:
    if option not in args:
        args.extend([option, value])


def _default_input_payload(contract: dict[str, Any]) -> str:
    schema = contract.get("input_schema")
    if isinstance(schema, dict) and isinstance(schema.get("example"), dict):
        return json.dumps(schema["example"], ensure_ascii=False, separators=(",", ":"))
    return "{}"


def _resolve_lgwf_py(args: list[str]) -> Path:
    raw = _pop_option(args, "--lgwf-py") or os.environ.get("LGWF_PY")
    if not raw:
        raise ValueError("LGWF runtime path is required: pass --lgwf-py or set LGWF_PY")
    path = Path(raw)
    if not path.is_file():
        raise ValueError(f"LGWF runtime not found: {path}")
    return path


def _prepare_contract_args(args: list[str], temp_dir: Path) -> tuple[Path, list[str]]:
    prepared = list(args)
    lgwf_py = _resolve_lgwf_py(prepared)
    workflow_id = _pop_option(prepared, "--workflow-id")
    if workflow_id is None:
        return lgwf_py, prepared

    workflow, contract = _load_registry_workflow(workflow_id)
    if workflow.get("kind") != "lgwf":
        raise ValueError(f"--workflow-id {workflow_id} is not an LGWF workflow")

    input_json = _pop_option(prepared, "--input-json")
    input_json_file = _pop_option(prepared, "--input-json-file")
    auto_human = _pop_flag(prepared, "--auto-human")
    if input_json is not None and input_json_file is not None:
        raise ValueError("--input-json and --input-json-file cannot be combined")
    if contract.get("input_mode") == "input_json_required" and input_json is None and input_json_file is None:
        raise ValueError(f"--workflow-id {workflow_id} requires input JSON")
    if auto_human and contract.get("auto_human_policy") == "forbidden":
        raise ValueError(f"--workflow-id {workflow_id} forbids --auto-human")

    _insert_option_if_missing(prepared, "--workflow-lgwf", workflow["workflow_lgwf"])
    _insert_option_if_missing(prepared, "--work-dir", workflow["work_dir"])

    if input_json_file is not None:
        prepared.extend(["--input-json-file", input_json_file])
    else:
        payload = input_json if input_json is not None else _default_input_payload(contract)
        json.loads(payload)
        input_path = temp_dir / f"{workflow_id}-input.json"
        input_path.write_text(payload, encoding="utf-8")
        prepared.extend(["--input-json-file", str(input_path)])
    if auto_human:
        prepared.append("--auto-human")
    return lgwf_py, prepared


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        with tempfile.TemporaryDirectory(prefix="facade-template-input-") as tmp:
            lgwf_py, prepared_args = _prepare_contract_args(args, Path(tmp))
            command = [sys.executable, str(lgwf_py), "run", *prepared_args]
            completed = subprocess.run(command, cwd=str(FACADE_ROOT))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
