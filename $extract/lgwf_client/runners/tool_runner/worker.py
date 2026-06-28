import argparse
import json
import pathlib
from typing import Any

import lgwf_client.tools.registry as tool_registry_module


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request-json", required=True)
    args = parser.parse_args(argv)

    try:
        request = json.loads(pathlib.Path(args.request_json).read_text(encoding="utf-8"))
        if not isinstance(request, dict):
            raise ValueError("tool request must be a JSON object.")
        options = request.get("options")
        if not isinstance(options, dict):
            raise ValueError("tool options must be a JSON object.")
        result = tool_registry_module.run_builtin_tool(
            request.get("tool"),
            options,
            pathlib.Path(request.get("workspace_root", "")),
        )
        envelope: dict[str, Any] = {"ok": True, "result": result}
    except Exception as exc:
        envelope = {
            "ok": False,
            "error_type": type(exc).__name__,
            "message": str(exc),
        }
    print(json.dumps(envelope, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
