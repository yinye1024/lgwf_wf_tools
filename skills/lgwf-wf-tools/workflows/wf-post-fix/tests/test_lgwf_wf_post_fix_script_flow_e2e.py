from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from typing import Any


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
WF_ROOT = PACKAGE_ROOT / "wf"


def load_module(relative: str, name: str):
    path = WF_ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


@contextlib.contextmanager
def pushd(path: Path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def run_main(module) -> dict[str, Any]:
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        module.main()
    return json.loads(stdout.getvalue())


def make_target_package(root: Path) -> dict[str, Any]:
    package_root = root / "demo-post-target"
    package_root.mkdir()
    workflow_lgwf = package_root / "workflow.lgwf"
    workflow_lgwf.write_text("WORKFLOW demo_post_target;\nENTRY noop;\n", encoding="utf-8")
    return {
        "target_workflow_lgwf": str(workflow_lgwf),
        "target_package_root": str(package_root),
        "target_dirs": [str(package_root)],
        "mode": "manual",
    }


class LgwfWfPostFixScriptFlowE2ETest(unittest.TestCase):
    maxDiff = None

    def test_target_mapper_e2e_request_and_summary_do_not_request_real_happy_tests(self) -> None:
        normalize = load_module("01_prepare_target/scripts/normalize_post_fix_target.py", "post_fix_e2e_normalize")
        build_prompt_fix = load_module("02_prompt_fix/scripts/build_prompt_fix_input.py", "post_fix_e2e_prompt_fix")
        build_prompt_upgrade = load_module(
            "03_prompt_upgrade/scripts/build_prompt_upgrade_input.py",
            "post_fix_e2e_prompt_upgrade",
        )
        build_e2e = load_module("04_e2e_generate/scripts/build_e2e_input.py", "post_fix_e2e_build_e2e")
        summarize = load_module("09_finish/scripts/summarize_post_fix.py", "post_fix_e2e_summarize")

        with tempfile.TemporaryDirectory(prefix="lgwf-post-fix-script-flow-") as temp:
            workspace = Path(temp)
            target = make_target_package(workspace)
            with pushd(workspace):
                write_json(Path(".lgwf/post_fix_target.request.json"), {"post_fix_target": target})
                normalize_payload = run_main(normalize)
                normalized = normalize_payload["lgwf_wf_post_fix.post_fix_target"]

                self.assertEqual(normalized, target)
                self.assertFalse(read_json(Path(".lgwf/post_fix_decisions.json"))["auto_enabled"])
                self.assertEqual(
                    {
                        "prompt_fix_target": {
                            "target_workflow_lgwf": target["target_workflow_lgwf"],
                            "target_package_root": target["target_package_root"],
                            "target_dirs": target["target_dirs"],
                        }
                    },
                    build_prompt_fix.build_prompt_fix_input(normalized),
                )
                self.assertEqual(
                    target["target_workflow_lgwf"],
                    build_prompt_upgrade.build_prompt_upgrade_input(normalized)["prompt_upgrade_target"][
                        "target_workflow_lgwf"
                    ],
                )

                e2e_input = build_e2e.build_e2e_input(normalized)
                self.assertEqual(["script_flow", "runtime_fake"], e2e_input["test_types"])
                self.assertNotIn("real_positive", e2e_input["test_types"])
                self.assertNotIn("wf_fix_positive", e2e_input["test_types"])

                summary_payload = run_main(summarize)
                summary = summary_payload["lgwf_wf_post_fix.post_fix_summary"]
                self.assertEqual(summary["target"], target)
                self.assertEqual(read_json(Path(".lgwf/post_fix_summary.json"))["target"], target)
                self.assertTrue(Path("reports/wf-post-fix/report.md").is_file())

    def test_generated_script_and_runtime_fake_entrypoints_are_executed_and_recorded(self) -> None:
        run_script_flow = load_module(
            "05_run_generated_tests/scripts/run_script_flow_e2e.py",
            "post_fix_e2e_run_script_flow",
        )
        run_runtime_fake = load_module(
            "06_runtime_fake_e2e/scripts/run_runtime_fake_e2e.py",
            "post_fix_e2e_run_runtime_fake",
        )

        with tempfile.TemporaryDirectory(prefix="lgwf-post-fix-generated-tests-") as temp:
            workspace = Path(temp)
            target = make_target_package(workspace)
            tests_dir = Path(target["target_package_root"]) / "tests"
            script_test = tests_dir / "test_demo_post_target_script_flow_e2e.py"
            runtime_test = tests_dir / "test_demo_post_target_runtime_fake_e2e.py"
            script_test.parent.mkdir(parents=True)
            script_test.write_text("print('script flow ok')\n", encoding="utf-8")
            runtime_test.write_text("print('runtime fake ok')\n", encoding="utf-8")

            with pushd(workspace):
                write_json(Path(".lgwf/post_fix_target.json"), target)
                write_json(Path(".lgwf/post_fix_decisions.json"), {"auto_enabled": False, "stages": []})
                write_json(Path(".lgwf/post_fix_decisions/script_flow_e2e.json"), {"decision": "run"})
                write_json(Path(".lgwf/post_fix_decisions/runtime_fake_e2e.json"), {"decision": "run"})

                script_payload = run_main(run_script_flow)
                runtime_payload = run_main(run_runtime_fake)

                self.assertEqual("continue", script_payload["__route__route_script_flow_e2e"])
                self.assertEqual("continue", runtime_payload["__route__route_runtime_fake_e2e"])
                self.assertEqual(
                    "completed",
                    script_payload["lgwf_wf_post_fix.script_flow_e2e_result"]["status"],
                )
                self.assertEqual(
                    "completed",
                    runtime_payload["lgwf_wf_post_fix.runtime_fake_e2e_result"]["status"],
                )
                stages = read_json(Path(".lgwf/post_fix_stage_results.json"))["stages"]
                self.assertEqual([item["stage_id"] for item in stages], ["script_flow_e2e", "runtime_fake_e2e"])
                self.assertTrue(all(item["status"] == "completed" for item in stages))

    def test_summary_uses_latest_stage_result_and_preserves_history(self) -> None:
        summarize = load_module("09_finish/scripts/summarize_post_fix.py", "post_fix_e2e_summary_latest")

        with tempfile.TemporaryDirectory(prefix="lgwf-post-fix-summary-latest-") as temp:
            workspace = Path(temp)
            target = make_target_package(workspace)
            with pushd(workspace):
                write_json(Path(".lgwf/post_fix_target.json"), target)
                write_json(Path(".lgwf/post_fix_decisions.json"), {"auto_enabled": True, "stages": []})
                write_json(
                    Path(".lgwf/post_fix_stage_results.json"),
                    {
                        "stages": [
                            {"stage_id": "script_flow_e2e", "status": "skipped"},
                            {"stage_id": "runtime_fake_e2e", "status": "completed"},
                            {"stage_id": "script_flow_e2e", "status": "completed"},
                        ]
                    },
                )

                payload = run_main(summarize)

            summary = payload["lgwf_wf_post_fix.post_fix_summary"]
            self.assertEqual(
                [
                    {"stage_id": "script_flow_e2e", "status": "completed"},
                    {"stage_id": "runtime_fake_e2e", "status": "completed"},
                ],
                summary["stages"],
            )
            self.assertEqual(3, len(summary["stage_history"]))

    def test_finish_e2e_generate_materializes_child_generated_tests(self) -> None:
        finish_e2e = load_module(
            "04_e2e_generate/scripts/finish_e2e_generate_stage.py",
            "post_fix_e2e_finish_generate",
        )

        with tempfile.TemporaryDirectory(prefix="lgwf-post-fix-materialize-") as temp:
            repo = Path(temp) / "repo"
            workspace = repo / "skills/lgwf-wf-tools/workflows/wf-post-fix/ws"
            target_root = repo / "skills/lgwf-wf-tools/workflows/skill-packaging"
            child_root = workspace / ".lgwf/isolations/run_workflow/e2e_generate/workspace/workflows/skill-packaging"
            report_path = workspace / ".lgwf/isolations/run_workflow/e2e_generate/work_dir/reports/e2e-test-generator/report.json"

            (target_root / "wf").mkdir(parents=True)
            (target_root / "wf/workflow.lgwf").write_text("WORKFLOW skill_packaging;\n", encoding="utf-8")
            (child_root / "tests").mkdir(parents=True)
            (child_root / "tests/test_wf_script_flow_e2e.py").write_text(
                "print('materialized script flow')\n",
                encoding="utf-8",
            )
            (child_root / "tests/test_wf_runtime_fake_e2e.py").write_text(
                "print('materialized runtime fake')\n",
                encoding="utf-8",
            )
            write_json(
                report_path,
                {
                    "target": {
                        "workflow_root": str(child_root),
                        "test_output_dir": "tests",
                        "generated_tests": {
                            "script_flow": "test_wf_script_flow_e2e.py",
                            "runtime_fake": "test_wf_runtime_fake_e2e.py",
                        },
                    },
                    "selected_test_types": ["script_flow", "runtime_fake"],
                    "generated_tests": {
                        "script_flow": "test_wf_script_flow_e2e.py",
                        "runtime_fake": "test_wf_runtime_fake_e2e.py",
                    },
                },
            )

            target = {
                "target_workflow_lgwf": "skills\\lgwf-wf-tools\\workflows\\skill-packaging\\wf\\workflow.lgwf",
                "target_package_root": "skills\\lgwf-wf-tools\\workflows\\skill-packaging",
                "target_dirs": ["skills\\lgwf-wf-tools\\workflows\\skill-packaging"],
                "mode": "auto",
            }
            with pushd(workspace):
                write_json(Path(".lgwf/post_fix_target.json"), target)
                write_json(
                    Path(".lgwf/post_fix_decisions.json"),
                    {
                        "auto_enabled": True,
                        "stages": [
                            {
                                "stage_id": "e2e_generate",
                                "decision": "run",
                                "route": "run",
                                "source": "auto",
                                "reason": "auto",
                            }
                        ],
                    },
                )

                payload = run_main(finish_e2e)

            script_dest = target_root / "tests/test_wf_script_flow_e2e.py"
            runtime_dest = target_root / "tests/test_wf_runtime_fake_e2e.py"
            self.assertEqual("continue", payload["__route__e2e_generate_stage"])
            self.assertEqual("print('materialized script flow')\n", script_dest.read_text(encoding="utf-8"))
            self.assertEqual("print('materialized runtime fake')\n", runtime_dest.read_text(encoding="utf-8"))

            materialized = read_json(workspace / ".lgwf/post_fix_generated_tests.materialized.json")
            self.assertEqual("copied", materialized["status"])
            self.assertEqual(
                {
                    "script_flow_e2e": script_dest.resolve(),
                    "runtime_fake_e2e": runtime_dest.resolve(),
                },
                {
                    key: Path(materialized["generated_tests"][key]).resolve()
                    for key in ("script_flow_e2e", "runtime_fake_e2e")
                },
            )
            self.assertEqual(read_json(workspace / ".lgwf/post_fix_generated_tests.json"), materialized["generated_tests"])


if __name__ == "__main__":
    unittest.main()
