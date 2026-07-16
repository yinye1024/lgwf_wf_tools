from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PACKAGE_ROOT / "wf" / "04_main_agent_handoff" / "scripts" / "prepare_main_agent_handoff.py"


def load_handoff_module():
    spec = importlib.util.spec_from_file_location("wf_create_fast_prepare_main_agent_handoff", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载 {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class MainAgentHandoffTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_handoff_module()

    def test_writes_handoff_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work_dir = Path(tmp)
            lgwf_dir = work_dir / ".lgwf"
            lgwf_dir.mkdir()
            (lgwf_dir / "materialize_scaffold_result.json").write_text(
                json.dumps(
                    {
                        "status": "ok",
                        "target_package_root": "skills/example-workflow",
                        "target_package_abs": "D:/allen/github/lgwf_wf_tools/skills/example-workflow",
                        "validation_commands": [
                            "python skills/lgwf-wf-tools/vendor/lgwf-client-assist/scripts/lgwf.py audit --workflow-lgwf skills/example-workflow/wf/workflow.lgwf",
                            "python -m unittest discover skills/example-workflow/tests",
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            payload = self.module.prepare_main_agent_handoff(work_dir)

            self.assertEqual(payload["workflow_id"], "wf-create-fast")
            self.assertEqual(payload["next_action"], "main_agent_authoring")
            self.assertEqual(payload["edit_dirs"], ["skills/example-workflow"])
            self.assertEqual(payload["target_workflow_lgwf"], "skills/example-workflow/wf/workflow.lgwf")
            self.assertIn(".lgwf/scaffold_package_result.json", payload["source_artifacts"])
            self.assertIn(".lgwf/materialize_scaffold_result.json", payload["source_artifacts"])
            self.assertFalse(payload["requires_user_confirmation"])
            self.assertFalse(payload["auto_execute_downstream_workflow"])
            written = json.loads((lgwf_dir / "main_agent_authoring_handoff.json").read_text(encoding="utf-8"))
            self.assertEqual(written, payload)

    def test_handoff_prompt_forbids_standard_back_half(self) -> None:
        prompt = (PACKAGE_ROOT / "wf" / "04_main_agent_handoff" / "handoff_main_agent_authoring.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("step_designs.json", prompt)
        self.assertIn("03_confirm_step_designs", prompt)
        self.assertIn("04_implement_steps_react", prompt)
        self.assertIn("不自动启动 `wf-post-fix`", prompt)


if __name__ == "__main__":
    unittest.main()
