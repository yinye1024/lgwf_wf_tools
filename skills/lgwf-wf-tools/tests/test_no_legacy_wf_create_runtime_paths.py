from __future__ import annotations

import unittest
from pathlib import Path


FACADE_ROOT = Path(__file__).resolve().parents[1]
WF_CREATE_WF = FACADE_ROOT / "workflows" / "wf-create" / "wf"


class NoLegacyWfCreateRuntimePathsTest(unittest.TestCase):
    def test_wf_create_runtime_python_uses_current_wf_structure_only(self) -> None:
        offenders: list[str] = []
        forbidden_fragments = (
            "workflows/wf-create/scripts",
            ".lgwf/scripts",
        )
        for path in WF_CREATE_WF.rglob("*.py"):
            text = path.read_text(encoding="utf-8").replace("\\", "/")
            for fragment in forbidden_fragments:
                if fragment in text:
                    offenders.append(f"{path.relative_to(WF_CREATE_WF).as_posix()}: {fragment}")
        self.assertEqual([], offenders)


if __name__ == "__main__":
    unittest.main()
