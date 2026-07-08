from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared" / "scripts"))

from audit_fix_common import copy_tree, lgwf_dir, load_runtime_context, output_state, read_json, write_json


def main() -> None:
    context = load_runtime_context()
    snapshot = read_json(lgwf_dir() / "candidate_pass_snapshot.json", {})
    source = Path(str(snapshot["candidate_package_root"]))
    target = Path(str(context["resolved_target_package_root"]))
    copy_tree(source, target)
    result = {"promoted": True, "source": str(source), "target": str(target)}
    write_json(lgwf_dir() / "promote_result.json", result)
    output_state({"promote_result": result})


if __name__ == "__main__":
    main()
