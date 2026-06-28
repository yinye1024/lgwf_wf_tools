import json

import _common
import lgwf_client.tools.registry as tool_registry_module


def main() -> int:
    result = tool_registry_module.run_builtin_tool(
        "write_text_file",
        _common.load_options(),
        _common.workspace_root(),
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
