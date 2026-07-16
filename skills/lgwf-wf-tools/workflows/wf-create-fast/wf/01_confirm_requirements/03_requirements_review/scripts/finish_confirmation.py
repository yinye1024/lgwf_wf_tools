"""结束需求确认分支，不固化 confirmed artifact。"""

from __future__ import annotations

import json


def main() -> None:
    print(json.dumps({"lgwf_wf_create_fast.requirements_confirmation_finished": True}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
