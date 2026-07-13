from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


FACADE_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = FACADE_ROOT / "scripts" / "doctor_lgwf_wf_tools.py"


def load_doctor_module():
    sys.path.insert(0, str(SCRIPT_PATH.parent))
    spec = importlib.util.spec_from_file_location("doctor_lgwf_wf_tools", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DoctorDeepTest(unittest.TestCase):
    def test_deep_doctor_writes_repair_report_files(self) -> None:
        module = load_doctor_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            facade = root / "facade"
            facade.mkdir()
            (facade / "SKILL.md").write_text("# skill\n", encoding="utf-8")
            registry_path = facade / "registry.json"
            registry_path.write_text(
                json.dumps(
                    {
                        "workflows": [
                            {
                                "id": "fake",
                                "kind": "lgwf",
                                "workflow_lgwf": "workflows/fake/workflow.lgwf",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            workflow_lgwf = facade / "workflows" / "fake" / "workflow.lgwf"
            workflow_lgwf.parent.mkdir(parents=True)
            workflow_lgwf.write_text("WORKFLOW fake;\nENTRY run;\n", encoding="utf-8")

            vendor = facade / "vendor" / "lgwf-client-assist"
            scripts = vendor / "scripts"
            assets = vendor / "assets"
            scripts.mkdir(parents=True)
            assets.mkdir()
            (vendor / "AGENTS.md").write_text("# vendor\n", encoding="utf-8")
            (assets / "lgwf-0.0.0-py3-none-any.whl").write_text("", encoding="utf-8")
            fake_lgwf = scripts / "lgwf.py"
            fake_lgwf.write_text(
                "\n".join(
                    [
                        "import json, sys",
                        "if sys.argv[1] == 'doctor':",
                        "    print(json.dumps({'passed': True}))",
                        "    raise SystemExit(0)",
                        "if sys.argv[1] == 'audit':",
                        "    print(json.dumps({",
                        "        'passed': False,",
                        "        'workflow': {'name': 'fake'},",
                        "        'input': sys.argv[2],",
                        "        'summary': 'Workflow authoring audit found 1 issue(s).',",
                        "        'diagnostics': [{",
                        "            'severity': 'warning',",
                        "            'code': 'LGWF_NODE_FILE_INPUT_UNPRODUCED',",
                        "            'location': 'workflow.lgwf:1:1',",
                        "            'message': 'run reads workspace file .lgwf/result.json but no workflow node obviously writes it.'",
                        "        }]",
                        "    }, ensure_ascii=False))",
                        "    raise SystemExit(1)",
                    ]
                ),
                encoding="utf-8",
            )

            module.FACADE_ROOT = facade
            module.REGISTRY_PATH = registry_path
            module.ROOT_SKILL_MD = facade / "SKILL.md"
            module.VENDOR_ROOT = vendor
            module.VENDOR_AGENTS_MD = vendor / "AGENTS.md"
            module.VENDOR_SKILL_MD = vendor / "SKILL.md"
            module.LGWF_PY = fake_lgwf
            module.DOCTOR_LOCAL_DIR = facade / ".local" / "doctor"
            module.run_validation = lambda: {"passed": True}
            module.run_module_contract_validation = lambda: {"label": "module_contracts", "passed": True}

            result = module.run_doctor(deep=True)

            artifacts = result["artifacts"]
            run_dir = Path(artifacts["run_dir"])
            doctor_json = Path(artifacts["doctor_json"])
            doctor_md = Path(artifacts["doctor_md"])
            self.assertTrue(run_dir.is_dir())
            self.assertTrue(doctor_json.is_file())
            self.assertTrue(doctor_md.is_file())
            self.assertTrue(Path(artifacts["latest_json"]).is_file())
            self.assertTrue(Path(artifacts["latest_md"]).is_file())

            workflow_audit = run_dir / "workflow-audits" / "fake.json"
            self.assertTrue(workflow_audit.is_file())
            payload = json.loads(workflow_audit.read_text(encoding="utf-8"))
            self.assertEqual("LGWF_NODE_FILE_INPUT_UNPRODUCED", payload["diagnostics"][0]["code"])
            report_text = doctor_md.read_text(encoding="utf-8")
            self.assertIn("workflow_audit.fake", report_text)
            self.assertIn("LGWF_NODE_FILE_INPUT_UNPRODUCED", report_text)
            saved_result = json.loads(doctor_json.read_text(encoding="utf-8"))
            self.assertEqual(saved_result["artifacts"]["doctor_md"], str(doctor_md))

    def test_deep_doctor_runs_and_writes_latest_report(self) -> None:
        module = load_doctor_module()
        result = module.run_doctor(deep=True)
        self.assertIn("artifacts", result)
        self.assertTrue(Path(result["artifacts"]["doctor_json"]).is_file())
        self.assertTrue(Path(result["artifacts"]["doctor_md"]).is_file())
        self.assertTrue(Path(result["artifacts"]["latest_json"]).is_file())
        self.assertTrue(Path(result["artifacts"]["latest_md"]).is_file())
        self.assertTrue(result["deep_checks"])

    def test_deep_doctor_checks_module_contracts(self) -> None:
        module = load_doctor_module()
        result = module.run_doctor(deep=True)
        module_checks = [
            item
            for item in result.get("deep_checks", [])
            if item.get("label") == "module_contracts"
        ]
        self.assertEqual(1, len(module_checks))
        self.assertTrue(module_checks[0]["passed"])

    def test_module_contract_validation_ignores_unregistered_sibling_skills(self) -> None:
        module = load_doctor_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            facade = repo / "skills" / "lgwf-wf-tools"
            sibling = repo / "skills" / "repo-context-pack"
            sibling.mkdir(parents=True)
            share = facade / "workflows" / "01-share"
            share.mkdir(parents=True)
            (share / "module-contract.md").write_text(
                "codex_skill lgwf_workflow_package tool_workflow\n"
                "模块定位 入口 依赖 状态 产物 验证 禁止\n",
                encoding="utf-8",
            )
            (share / "entry-contract.md").write_text(
                "input_mode auto_human_policy entry_contract.json\n",
                encoding="utf-8",
            )
            agents = facade / "workflows" / "fake" / "AGENTS.md"
            agents.parent.mkdir(parents=True)
            agents.write_text("module-contract.md\nlgwf_workflow_package\n", encoding="utf-8")
            registry = facade / "registry.json"
            registry.write_text(
                json.dumps(
                    {
                        "workflows": [
                            {
                                "id": "fake",
                                "kind": "lgwf",
                                "agents_md": "workflows/fake/AGENTS.md",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            module.FACADE_ROOT = facade
            module.REPO_ROOT = repo
            module.SKILLS_ROOT = repo / "skills"
            module.REGISTRY_PATH = registry
            module.MODULE_CONTRACT_PATH = share / "module-contract.md"
            module.ENTRY_CONTRACT_PATH = share / "entry-contract.md"

            result = module.run_module_contract_validation()

        self.assertTrue(result["passed"], result)


if __name__ == "__main__":
    unittest.main()
