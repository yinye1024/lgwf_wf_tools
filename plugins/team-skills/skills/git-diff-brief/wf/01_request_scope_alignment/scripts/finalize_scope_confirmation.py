from __future__ import annotations

import json


def main() -> None:
    payload = {
        "git_diff_brief.finalize_scope_confirmation_result": {
            "ok": True,
            "confirmed_outputs": [
                "repository_input_context",
                "summary_scope",
                "scope_confirmation_result",
            ],
        }
    }
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
