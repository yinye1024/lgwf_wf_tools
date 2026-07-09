"""规范化打包请求并写入首轮路径上下文。"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


SHARED_SCRIPTS = Path(__file__).resolve().parents[2] / "shared" / "scripts"
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))

from packaging_common import bool_value, output_skill_path, read_stdin_object, resolve_user_path, write_json


def _request(payload: dict[str, Any]) -> dict[str, Any]:
    request = payload.get("packaging_request", payload)
    return request if isinstance(request, dict) else {}


def main() -> None:
    root = Path.cwd()
    payload = read_stdin_object()
    request = _request(payload)

    source_skill = str(request.get("source_skill", "")).strip()
    output_parent = str(request.get("output_parent", "")).strip()
    runtime_source = str(request.get("runtime_source", "")).strip()
    if not source_skill:
        raise ValueError("packaging_request.source_skill 不能为空")
    if not output_parent:
        raise ValueError("packaging_request.output_parent 不能为空")

    source_skill_abs = resolve_user_path(root, source_skill)
    output_parent_abs = resolve_user_path(root, output_parent)
    output_skill_abs = output_skill_path(source_skill_abs, output_parent_abs)

    packaging_request = {
      "source_skill": source_skill,
      "source_skill_abs": str(source_skill_abs),
      "output_parent": output_parent,
      "output_parent_abs": str(output_parent_abs),
      "output_skill_abs": str(output_skill_abs),
      "runtime_source": runtime_source,
      "runtime_source_abs": "",
      "force": bool_value(request.get("force"), False),
      "audit_smoke": bool_value(request.get("audit_smoke"), True),
    }
    path_context = {
      "workspace_root": str(resolve_user_path(root, ".")),
      "work_dir": str(root.resolve()),
      "source_skill_name": source_skill_abs.name,
      "output_skill_abs": str(output_skill_abs),
      "allowed_write_root_abs": str(output_parent_abs),
    }

    lgwf_dir = root / ".lgwf"
    write_json(lgwf_dir / "packaging_request.json", packaging_request)
    write_json(lgwf_dir / "packaging_path_context.json", path_context)
    print(
        json.dumps(
            {
                "skill_packaging.packaging_request": packaging_request,
                "skill_packaging.path_context": path_context,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
