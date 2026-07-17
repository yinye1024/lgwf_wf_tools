"""合并 inspection 的 Python 与 Codex Observe。"""

from __future__ import annotations

import json
import sys
from pathlib import Path


SHARED_SCRIPTS = Path(__file__).resolve().parents[3] / "shared" / "scripts"
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))

from observe_protocol import merge_observer_reports, write_json


def main() -> None:
    lgwf_dir = Path.cwd() / ".lgwf"
    merged = merge_observer_reports(
        stage="inspection",
        artifact_path=lgwf_dir / "prompt_workflow_inspection.json",
        python_report_path=lgwf_dir / "prompt_workflow_inspection_observe_py.json",
        codex_report_path=lgwf_dir / "prompt_workflow_inspection_observe_codex.json",
    )
    write_json(lgwf_dir / "prompt_workflow_inspection_observe.json", merged)
    print(json.dumps({"lgwf_wf_convert.inspect_observe": merged}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
