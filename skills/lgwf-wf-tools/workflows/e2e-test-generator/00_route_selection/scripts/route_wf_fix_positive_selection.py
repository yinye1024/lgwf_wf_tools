from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from route_selection_common import route_payload


def main() -> None:
    print(json.dumps(route_payload("route_wf_fix_positive_selection", "wf_fix_positive"), ensure_ascii=False))


if __name__ == "__main__":
    main()
