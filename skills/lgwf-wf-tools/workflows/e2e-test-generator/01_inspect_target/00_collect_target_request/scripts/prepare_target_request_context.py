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
                "instruction": "确认要为哪个目标 LGWF workflow 生成四类端到端测试。",
                "required_fields": {
                    "workflow_lgwf": "目标 workflow.lgwf 路径，可以是绝对路径或相对当前 work_dir 的路径。"
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
            }
        }
    )


if __name__ == "__main__":
    main()
