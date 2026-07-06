from __future__ import annotations

import importlib.util
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


class PipelinePlaceholderTests(unittest.TestCase):
    def test_placeholder_sentinel_is_stable(self) -> None:
        module = load_module("wf/wf_01_collect_targets_placeholder.py", "wf_dsl_upgrade_placeholder")
        self.assertEqual("wf-dsl-upgrade-draft", module.SENTINEL)

    def test_helper_read_json_returns_default_for_missing_file(self) -> None:
        module = load_module("wf/shared/scripts/upgrade_helpers.py", "upgrade_helpers")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "missing.json"
            self.assertEqual({"ok": True}, module.read_json(path, {"ok": True}))


if __name__ == "__main__":
    unittest.main()
