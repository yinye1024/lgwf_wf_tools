from __future__ import annotations

import base64
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
import argparse
from pathlib import Path
from unittest import mock


FACADE_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = FACADE_ROOT / "scripts" / "safe_approval_submit.py"


def load_script():
    spec = importlib.util.spec_from_file_location("safe_approval_submit", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class SafeApprovalSubmitTests(unittest.TestCase):
    def test_approval_approve_value_file_is_rejected(self) -> None:
        module = load_script()
        args = argparse.Namespace(
            kind="approval",
            work_dir="ws",
            request_id="human-1",
            decision="approve",
            route=None,
            comment="",
        )

        with self.assertRaisesRegex(ValueError, "approval approve does not accept value-json"):
            module.build_command(
                args,
                {"approval": "approve", "comment": "确认提交"},
            )

    def test_review_submit_reads_utf8_base64_and_uses_route(self) -> None:
        module = load_script()
        payload = json.dumps({"approval": "revise", "comment": "需要修订"}, ensure_ascii=False).encode("utf-8")
        encoded = base64.b64encode(payload).decode("ascii")
        calls: list[list[str]] = []

        def fake_run(args: list[str], **kwargs):
            calls.append(args)
            return subprocess.CompletedProcess(args=args, returncode=0, stdout='{"ok":true}', stderr="")

        with mock.patch.object(module.subprocess, "run", fake_run):
            exit_code = module.main(
                [
                    "--kind",
                    "review",
                    "--work-dir",
                    "ws",
                    "--request-id",
                    "human-2",
                    "--route",
                    "revise",
                    "--value-json-base64",
                    encoded,
                ]
            )

        self.assertEqual(0, exit_code)
        self.assertEqual("review", calls[0][2])
        self.assertEqual("submit", calls[0][3])
        self.assertIn("--route", calls[0])
        self.assertNotIn("--decision", calls[0])
        value_json = calls[0][calls[0].index("--value-json") + 1]
        self.assertTrue(value_json.isascii())
        self.assertEqual("需要修订", json.loads(value_json)["comment"])


if __name__ == "__main__":
    unittest.main()
