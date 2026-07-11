from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_context_pack.py"


class BuildContextPackTests(unittest.TestCase):
    def test_generates_expected_artifacts_and_detects_modules(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            output = Path(tmp) / "out"
            (root / "skills" / "demo-skill").mkdir(parents=True)
            (root / "workflows" / "demo-flow" / "wf").mkdir(parents=True)
            (root / "tests").mkdir()
            (root / "node_modules" / "ignored").mkdir(parents=True)

            (root / "AGENTS.md").write_text(
                "# 指引\n\n- 文本必须使用 UTF-8 no BOM。\n- 不要修改 vendor 目录。\n",
                encoding="utf-8",
            )
            (root / "README.md").write_text(
                "# Demo\n\n```powershell\npython -m unittest discover tests\n```\n",
                encoding="utf-8",
            )
            (root / "skills" / "demo-skill" / "SKILL.md").write_text(
                "---\nname: demo-skill\ndescription: demo\n---\n\n# Demo\n",
                encoding="utf-8",
            )
            (root / "workflows" / "demo-flow" / "entry_contract.json").write_text("{}", encoding="utf-8")
            (root / "workflows" / "demo-flow" / "wf" / "workflow.lgwf").write_text("workflow demo\n", encoding="utf-8")
            (root / "node_modules" / "ignored" / "README.md").write_text("python ignored.py\n", encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--target-dir",
                    str(root),
                    "--output-dir",
                    str(output),
                    "--focus",
                    "workflow-authoring",
                    "--depth",
                    "normal",
                ],
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            summary = json.loads(completed.stdout)
            self.assertEqual(summary["module_count"], 2)
            for artifact in summary["artifacts"]:
                self.assertTrue((output / artifact).exists(), artifact)

            module_map = json.loads((output / "module_map.json").read_text(encoding="utf-8"))
            kinds = {module["kind"] for module in module_map["modules"]}
            self.assertIn("codex_skill", kinds)
            self.assertIn("lgwf_workflow_package", kinds)

            commands = json.loads((output / "command_inventory.json").read_text(encoding="utf-8"))
            command_text = "\n".join(item["command"] for item in commands["commands"])
            self.assertIn("python -m unittest discover tests", command_text)
            self.assertNotIn("ignored.py", command_text)


if __name__ == "__main__":
    unittest.main()
