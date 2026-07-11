from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def package_root() -> Path:
    return Path(__file__).resolve().parents[2]


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


def main() -> int:
    root = package_root()
    required_files = [
        "AGENTS.md",
        "README.md",
        "entry_contract.json",
        "wf/workflow.lgwf",
        "wf/artifact_contracts.json",
        "self-improve/manifest.json",
    ]
    required_dirs = [
        "tests",
        "ws",
    ]
    issues: list[str] = []
    for relative in required_files:
        if not (root / relative).is_file():
            issues.append(f"missing file: {relative}")
    for relative in required_dirs:
        if not (root / relative).is_dir():
            issues.append(f"missing dir: {relative}")

    contract_path = root / "entry_contract.json"
    if contract_path.is_file():
        contract = read_json(contract_path)
        if contract.get("kind") != "lgwf":
            issues.append("entry_contract.kind must be lgwf")
        if contract.get("workflow_lgwf") != "workflows/skill-packaging/wf/workflow.lgwf":
            issues.append("entry_contract.workflow_lgwf drift")
        if contract.get("work_dir") != "workflows/skill-packaging/ws":
            issues.append("entry_contract.work_dir drift")

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "passed": not issues,
        "issues": issues,
    }
    output = root / ".local" / "self-improve" / "check-latest.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "report": str(output)}, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
