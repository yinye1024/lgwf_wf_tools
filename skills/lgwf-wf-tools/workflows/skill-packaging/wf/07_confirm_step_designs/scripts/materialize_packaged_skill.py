from __future__ import annotations

import json
import sys


def main() -> None:
    plan = json.loads(sys.stdin.read() or "{}")
    result = {
        "status": "placeholder",
        "summary": "当前初稿只落地 workflow authoring 文件树，真实复制、runtime 内置和 manifest 生成待后续实现。",
        "expected_outputs": [
            "vendor/lgwf-client-assist/",
            "scripts/run_local_lgwf_workflow.py",
            "PACKAGING_MANIFEST.json",
        ],
        "source": plan,
    }
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
