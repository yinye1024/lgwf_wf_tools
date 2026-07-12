from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


FACADE_ROOT = Path(__file__).resolve().parents[1]
WHEEL = FACADE_ROOT / "vendor" / "lgwf-client-assist" / "assets" / "lgwf-0.1.2-py3-none-any.whl"


class CodexHandoffPromptBoundaryTests(unittest.TestCase):
    def test_handoff_prompt_includes_system_level_node_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_root = Path(temp)
            wheel_root = temp_root / "wheel"
            with zipfile.ZipFile(WHEEL) as archive:
                archive.extractall(wheel_root)

            sys.path.insert(0, str(wheel_root))
            try:
                from lgwf_client.runners.codex_runner.runner import CodexRunner

                workflow_root = temp_root / "workflow"
                workspace_root = temp_root / "workspace"
                (workflow_root / "agents").mkdir(parents=True)
                (workspace_root / ".lgwf").mkdir(parents=True)
                (workflow_root / "agents" / "prompt.md").write_text("Prompt body\n", encoding="utf-8")
                (workspace_root / ".lgwf" / "input.json").write_text("{}\n", encoding="utf-8")

                runner = CodexRunner(workflow_root=workflow_root, workspace_root=workspace_root)
                prompt_text, main_prompt_path, context_paths = runner._prompt_text(
                    str(workspace_root),
                    None,
                    {"root": "workflow", "type": "file", "path": "agents/prompt.md"},
                    context_refs=[
                        {"root": "workspace", "type": "file", "path": ".lgwf/input.json"},
                    ],
                    output_json_path=workspace_root / ".lgwf" / "out.json",
                    output_json_mode="file",
                    contract={
                        "reads_state": ["state.input"],
                        "writes_state": ["state.output"],
                        "reads_resources": [
                            {"root": "workspace", "type": "file", "path": ".lgwf/input.json"},
                        ],
                        "writes_resources": [
                            {"root": "workspace", "type": "file", "path": ".lgwf/out.json"},
                        ],
                    },
                )
            finally:
                try:
                    sys.path.remove(str(wheel_root))
                except ValueError:
                    pass
                for name in list(sys.modules):
                    if name == "lgwf_client" or name.startswith("lgwf_client."):
                        del sys.modules[name]
                shutil.rmtree(wheel_root, ignore_errors=True)

            self.assertIsNotNone(main_prompt_path)
            self.assertTrue(str(main_prompt_path).replace("\\", "/").endswith("/workflow/agents/prompt.md"))
            self.assertEqual(1, len(context_paths))
            self.assertIn("System-level LGWF node boundary", prompt_text)
            self.assertIn("contract-first", prompt_text)
            self.assertIn("reference-only", prompt_text)
            self.assertIn("output-file-required", prompt_text)
            self.assertIn("LGWF node contract (contract-first details)", prompt_text)
            self.assertIn(".lgwf/input.json", prompt_text)
            self.assertIn(".lgwf/out.json", prompt_text)
            self.assertIn("Codex-written JSON output (output-file-required)", prompt_text)


if __name__ == "__main__":
    unittest.main()
