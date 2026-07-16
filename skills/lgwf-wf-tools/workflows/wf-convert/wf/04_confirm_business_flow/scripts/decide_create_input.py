"""只根据 canonical proposal Observe 决定 ReAct 是否继续。"""

from __future__ import annotations

import json
import sys
from pathlib import Path


SHARED_SCRIPTS = Path(__file__).resolve().parents[2] / "shared" / "scripts"
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))

from observe_protocol import decide_next


def main() -> None:
    observe_path = Path.cwd() / ".lgwf" / "wf_create_fast_input_observe.json"
    print(json.dumps({"next": decide_next(observe_path, expected_stage="proposal")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
