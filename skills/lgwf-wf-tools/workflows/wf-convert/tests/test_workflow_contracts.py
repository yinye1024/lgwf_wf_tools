import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def load_module(relative_path: str, module_name: str):
    module_path = PACKAGE_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class IndexPromptFilesTests(unittest.TestCase):
    def test_build_inventory_skips_runtime_and_cache_dirs(self):
        module = load_module(
            "wf/04_confirm_business_flow/scripts/index_prompt_files.py",
            "index_prompt_files",
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "flow" / "agents").mkdir(parents=True)
            (root / "flow" / "workflow.lgwf").write_text("WORKFLOW demo;", encoding="utf-8")
            (root / ".lgwf" / "cache").mkdir(parents=True)
            (root / "__pycache__").mkdir()
            inventory = module.build_inventory(root)
        files = [item["path"] for item in inventory["files"]]
        self.assertEqual(files, ["flow/workflow.lgwf"])
        self.assertEqual(inventory["workflow_files"], ["flow/workflow.lgwf"])


class PreparePayloadTests(unittest.TestCase):
    def test_build_payload_rejects_invalid_relative_paths(self):
        module = load_module(
            "wf/07_confirm_step_designs/scripts/prepare_wf_create_payload.py",
            "prepare_wf_create_payload",
        )
        with self.assertRaises(ValueError):
            module.normalize_package_path("../outside", "target_package_root")

    def test_build_payload_uses_confirmed_input(self):
        module = load_module(
            "wf/07_confirm_step_designs/scripts/prepare_wf_create_payload.py",
            "prepare_wf_create_payload",
        )
        payload = module.build_payload(
            confirmed_input={
                "workflow_name": "wf-convert",
                "target_package_root": "skills/lgwf-wf-tools/workflows/wf-convert",
                "source_root": "samples/source-flow",
                "report_fields": ["summary"],
            },
            approval={
                "decision": "approve",
            },
            package_profile="internal_workflow_package",
        )
        self.assertEqual(payload["workflow_name"], "wf-convert")
        self.assertEqual(payload["source_root"], "samples/source-flow")
        self.assertEqual(payload["package_profile"], "internal_workflow_package")


class SummaryTests(unittest.TestCase):
    def test_build_report_sections(self):
        module = load_module(
            "wf/09_summarize_create_result/scripts/summarize_convert_result.py",
            "summarize_convert_result",
        )
        report = module.render_report(
            {
                "workflow_name": "wf-convert",
                "analysis_summary": ["发现 1 个 workflow"],
                "approved_input_summary": ["目标包路径已确认"],
                "payload_summary": ["已生成 wf-create payload"],
                "risks": ["缺少真实样例验证"],
            }
        )
        self.assertIn("# wf-convert 转换结果汇总", report)
        self.assertIn("## 未解决风险", report)


class RunWorkflowTests(unittest.TestCase):
    def test_workflow_uses_run_workflow_node_for_wf_create(self):
        workflow_text = (PACKAGE_ROOT / "wf/workflow.lgwf").read_text(encoding="utf-8")
        self.assertIn("RUN_WORKFLOW wf_create", workflow_text)
        self.assertIn('WORKFLOW "workflows/wf-create/wf/workflow.lgwf"', workflow_text)
        self.assertIn('WORK_DIR "workflows/wf-create/ws"', workflow_text)
        self.assertIn("INPUT state.lgwf_wf_convert.wf_create_payload.wf_create_payload", workflow_text)
        self.assertIn("RESULT state.lgwf_wf_convert.wf_create_result", workflow_text)
        self.assertNotIn("HANDOFF handoff_wf_create", workflow_text)
        self.assertNotIn("SCRIPT \"10_handoff_wf_create/scripts/handoff_wf_create.py\"", workflow_text)


if __name__ == "__main__":
    unittest.main()
