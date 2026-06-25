from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "shared"))

from e2e_generator_common import output_state


def main() -> None:
    output_state(
        {
            "target_request_context": {
                "instruction": "确认要为哪个目标 LGWF workflow 生成三类端到端测试。",
                "required_fields": {
                    "workflow_lgwf": "目标 workflow.lgwf 路径，可以是绝对路径或相对当前 work_dir 的路径。"
                },
                "optional_fields": {
                    "workflow_root": "目标 workflow package 根目录，默认 workflow_lgwf 所在目录。",
                    "test_output_dir": "测试输出目录，默认 tests。",
                    "test_name_prefix": "测试文件名前缀，默认从 WORKFLOW 名称推导。",
                    "real_codex_env": "真实 Codex E2E 开关环境变量，默认按测试前缀推导。",
                },
                "fixed_outputs": [
                    "test_<workflow>_script_flow_e2e.py",
                    "test_<workflow>_runtime_fake_e2e.py",
                    "test_<workflow>_real_positive_e2e.py",
                ],
            }
        }
    )


if __name__ == "__main__":
    main()
