from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
WF_ROOT = PACKAGE_ROOT / "wf"
sys.dont_write_bytecode = True


def load_module(relative: str, name: str):
    path = WF_ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def run_main(module) -> dict:
    output = StringIO()
    with redirect_stdout(output):
        module.main()
    text = output.getvalue()
    return json.loads(text or "{}")


class pushd:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.previous = Path.cwd()

    def __enter__(self) -> None:
        import os

        os.chdir(self.path)

    def __exit__(self, exc_type, exc, tb) -> None:
        import os

        os.chdir(self.previous)


class LgwfWfCreateScriptFlowE2ETest(unittest.TestCase):
    def test_confirmation_scripts_prepare_apply_and_summarize_artifacts(self) -> None:
        prepare_requirements = load_module(
            "01_confirm_requirements/scripts/prepare_requirements_confirmation.py",
            "e2e_prepare_requirements",
        )
        apply_requirements = load_module(
            "01_confirm_requirements/scripts/apply_confirmed_requirements.py",
            "e2e_apply_requirements",
        )
        prepare_business_flow = load_module(
            "02_confirm_business_flow/scripts/prepare_business_flow_confirmation.py",
            "e2e_prepare_business_flow",
        )
        apply_business_flow = load_module(
            "02_confirm_business_flow/scripts/apply_confirmed_business_flow.py",
            "e2e_apply_business_flow",
        )
        prepare_steps = load_module(
            "03_confirm_step_designs/scripts/prepare_step_design_confirmation.py",
            "e2e_prepare_steps",
        )
        apply_steps = load_module(
            "03_confirm_step_designs/scripts/apply_confirmed_step_designs.py",
            "e2e_apply_steps",
        )
        summarize = load_module(
            "06_summarize_create_result/scripts/summarize_create_result.py",
            "e2e_summarize",
        )

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lgwf_dir = root / ".lgwf"
            lgwf_dir.mkdir()
            (lgwf_dir / "create_requirements_proposal.json").write_text(
                json.dumps(
                    {
                        "workflow_name": "demo_create",
                        "target_package_root": "skills/demo-create",
                        "requirements": [{"id": "r1", "description": "生成 workflow package"}],
                    }
                ),
                encoding="utf-8",
            )
            (lgwf_dir / "business_flow_proposal.json").write_text(
                json.dumps(
                    {
                        "workflow_name": "demo_create",
                        "stages": [{"stage_id": "confirm_requirements", "key_nodes": ["confirm_requirements"]}],
                    }
                ),
                encoding="utf-8",
            )
            (lgwf_dir / "step_designs_proposal.json").write_text(
                json.dumps({"step_designs": [{"step_slug": "collect_raw_intent", "purpose": "收集原始意图"}]}),
                encoding="utf-8",
            )

            with pushd(root):
                for prepare_module, state_key in (
                    (prepare_requirements, "lgwf_wf_create.requirements_confirmation_context"),
                    (prepare_business_flow, "lgwf_wf_create.business_flow_confirmation_context"),
                    (prepare_steps, "lgwf_wf_create.step_design_confirmation_context"),
                ):
                    self.assertIn(state_key, run_main(prepare_module))

                (lgwf_dir / "create_requirements_approval.json").write_text(
                    json.dumps({"decision": "approve", "confirmed": {"workflow_name": "demo_create"}}),
                    encoding="utf-8",
                )
                (lgwf_dir / "business_flow_approval.json").write_text(
                    json.dumps({"decision": "approve", "confirmed": {"stages": [{"stage_id": "confirm_requirements"}]}}),
                    encoding="utf-8",
                )
                (lgwf_dir / "step_design_confirmation_record.json").write_text(
                    json.dumps({"decision": "approve", "confirmed": {"step_designs": [{"step_slug": "collect_raw_intent"}]}}),
                    encoding="utf-8",
                )

                self.assertIn("lgwf_wf_create.apply_requirements_result", run_main(apply_requirements))
                self.assertIn("lgwf_wf_create.apply_business_flow_result", run_main(apply_business_flow))
                self.assertIn("lgwf_wf_create.apply_step_designs_result", run_main(apply_steps))
                self.assertEqual(run_main(summarize)["status"], "draft_structure_ready")

            for name in ("create_requirements.json", "business_flow.json", "step_designs.json", "create_result_summary.json"):
                self.assertTrue((lgwf_dir / name).exists(), name)

            summary = json.loads((lgwf_dir / "create_result_summary.json").read_text(encoding="utf-8"))
            self.assertIn(".lgwf/create_requirements.json", summary["runtime_artifacts"])
            self.assertEqual(summary["status"], "draft_structure_ready")


if __name__ == "__main__":
    unittest.main()
