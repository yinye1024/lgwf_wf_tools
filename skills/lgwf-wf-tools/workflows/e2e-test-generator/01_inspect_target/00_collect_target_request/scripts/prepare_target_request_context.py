from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "shared"))

from e2e_generator_common import output_state


REQUEST_KEYS = ("workflow_lgwf", "workflow_root", "test_output_dir", "test_name_prefix", "test_types")


def read_stdin_object() -> dict[str, Any]:
    raw = sys.stdin.read().strip()
    if raw:
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise TypeError("stdin payload 必须是 JSON object")
        return payload
    fallback = Path.cwd() / ".lgwf" / "input_state.json"
    if fallback.is_file():
        payload = json.loads(fallback.read_text(encoding="utf-8-sig"))
        if isinstance(payload, dict):
            return payload
    return {}


def build_target_request(payload: dict[str, Any]) -> dict[str, Any]:
    for wrapper_key in ("e2e_target_request", "target_request"):
        wrapped = payload.get(wrapper_key)
        if isinstance(wrapped, dict):
            payload = wrapped
            break
    return {key: payload[key] for key in REQUEST_KEYS if key in payload}


def build_target_request_context(request: dict[str, Any]) -> dict[str, Any]:
    return {
        "instruction": "确认要为哪个目标 LGWF workflow 生成四类端到端测试。",
        "approval_target": "e2e_target_request",
        "persist_path": ".lgwf/e2e_target_request.json",
        "candidate_request": request,
        "required_fields": {
            "workflow_lgwf": "目标 workflow.lgwf 路径，可以是绝对路径或相对当前 work dir 的路径。"
        },
        "optional_fields": {
            "workflow_root": "目标 workflow package 根目录，默认 workflow_lgwf 所在目录。",
            "test_output_dir": "测试输出目录，默认 tests。",
            "test_name_prefix": "测试文件名前缀，默认从 WORKFLOW 名称推导。",
            "test_types": "要生成的测试类型列表，可选 script_flow、runtime_fake、real_positive、wf_fix_positive；省略或空数组表示全部生成。",
        },
        "fixed_outputs": [
            "test_<workflow>_script_flow_e2e.py",
            "test_<workflow>_runtime_fake_e2e.py",
            "lgwf_<workflow>_real_positive_e2e.py",
            "lgwf_<workflow>_real_positive_e2e_for_wf_fix.py",
        ],
        "auto_approval_note": "当 candidate_request 已包含 workflow_lgwf 时，approve 只确认该业务请求；不要把本说明上下文写入业务请求。",
    }


def main() -> None:
    payload = read_stdin_object()
    request = build_target_request(payload)
    output_state(
        {
            "target_request": request,
            "target_request_context": build_target_request_context(request),
        }
    )


if __name__ == "__main__":
    main()
