from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def load_manager():
    path = Path(__file__).resolve().parents[3] / "04_execute_react_loop" / "00_prepare" / "scripts" / "manage_react_task.py"
    spec = importlib.util.spec_from_file_location("manage_react_task", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load manage_react_task.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_safety_validator():
    path = (
        Path(__file__).resolve().parents[3]
        / "01_generate_plan"
        / "02_generate_plan_proposal"
        / "scripts"
        / "plan_contract_safety.py"
    )
    spec = importlib.util.spec_from_file_location("plan_contract_safety", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load plan_contract_safety.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_json(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"missing required artifact: {path}")
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise SystemExit(f"artifact must be a JSON object: {path}")
    return data


def approved(value: object) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"approve", "approved", "yes", "y"}
    if isinstance(value, dict):
        raw = str(value.get("approval") or value.get("decision") or value.get("status") or "").strip().lower()
        return raw in {"approve", "approved", "yes", "y"}
    return False


def main() -> None:
    root = Path.cwd()
    lgwf_dir = root / ".lgwf"
    request = read_json(lgwf_dir / "react_task_request.json")
    plan = read_json(lgwf_dir / "react_task_plan_proposal.json")
    acceptance = read_json(lgwf_dir / "react_acceptance_proposal.json")
    approval = read_json(lgwf_dir / "react_task_contract_approval.json")
    if not approved(approval):
        raise SystemExit("contract approval rejected")
    safety = load_safety_validator().validate_plan_contract(request, plan)
    if not safety.get("passed"):
        raise SystemExit("plan contract safety check failed: " + json.dumps(safety, ensure_ascii=False))
    manager = load_manager()
    manager.init_plan(root, plan)
    manager.set_acceptance(root, acceptance)
    print(json.dumps({"lgwf_plan.contracts_applied": True}, ensure_ascii=False))


if __name__ == "__main__":
    main()

