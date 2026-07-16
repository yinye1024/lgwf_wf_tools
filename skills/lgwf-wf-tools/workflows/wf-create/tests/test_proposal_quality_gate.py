from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
WF_ROOT = PACKAGE_ROOT / "wf"


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def design_for_file(path: str, *, owner: str = "prepare") -> dict:
    if path.endswith("workflow.lgwf"):
        kind = "lgwf_workflow"
        required_structure = ["包含 WORKFLOW、ENTRY、PY 节点、CONTRACT 和 FLOW。"]
        acceptance_notes = ["workflow.lgwf 必须声明 WORKFLOW、ENTRY、CONTRACT 和 FLOW。"]
    elif path.startswith("tests/") or "/tests/" in path:
        kind = "test"
        required_structure = ["覆盖关键文件存在性、路径边界和最小行为。"]
        acceptance_notes = ["测试必须可独立运行，并给出具体失败信息。"]
    elif path.endswith(".md"):
        kind = "markdown_doc"
        required_structure = ["说明模块定位、输入、输出、验证和禁止事项。"]
        acceptance_notes = ["文档必须覆盖定位、输入、输出、验证和禁止事项。"]
    elif path.endswith(".json"):
        kind = "json_contract"
        required_structure = ["说明顶层字段、必填字段和消费方。"]
        acceptance_notes = ["JSON 必须说明顶层字段、必填字段和消费方。"]
    else:
        kind = "resource"
        required_structure = ["说明文件结构。"]
        acceptance_notes = ["文件结构清晰。"]
    return {
        "path": path,
        "kind": kind,
        "owner_step": owner,
        "purpose": f"定义 {path} 的结构。",
        "required_structure": required_structure,
        "reads": ["读取已确认步骤设计。"],
        "writes": [f"实现阶段写入 {path}。"],
        "dependencies": ["依赖动态 step design contract。"],
        "acceptance_notes": acceptance_notes,
        "forbidden": ["不得包含完整源码字段。"],
        "source_refs": ["step_design_validation_contract"],
        "content_mode": "exact" if kind == "lgwf_workflow" else "contract",
        **(
            {"exact_content": "WORKFLOW demo;\nENTRY run;\nPY run SCRIPT \"scripts/run.py\" CONTRACT { WRITE workspace file \".lgwf/out.json\"; };\nFLOW run;\n"}
            if kind == "lgwf_workflow"
            else {}
        ),
        **(
            {
                "test_contract": {
                    "test_framework": "Python unittest",
                    "scope": ["关键文件存在性、路径边界和最小 DSL 结构。"],
                    "fixtures": ["使用隔离临时目录。"],
                    "acceptance": ["失败信息指向具体问题。"],
                }
            }
            if kind == "test"
            else {}
        ),
        **(
            {
                "markdown_contract": {
                    "sections": ["模块定位", "入口", "输入", "输出", "验证", "禁止事项"]
                }
            }
            if kind == "markdown_doc"
            else {}
        ),
        **(
            {
                "json_contract": {
                    "top_level_fields": ["status"],
                    "required": ["status"],
                    "consumer": "测试",
                }
            }
            if kind == "json_contract"
            else {}
        ),
    }


def design_for_dir(path: str, expected_files: list[str], *, owner: str = "prepare") -> dict:
    return {
        "path": path,
        "purpose": f"承载 {path} 相关文件。",
        "owner_step": owner,
        "expected_files": expected_files,
        "forbidden": ["不得承载运行态 .lgwf 状态。"],
        "source_refs": ["step_design_validation_contract"],
    }


def valid_step(stage_id: str, target_files: list[str], target_dirs: list[str]) -> dict:
    return {
        "step_slug": stage_id,
        "step_name": f"设计 {stage_id}",
        "stage_id": stage_id,
        "goal": "设计目标阶段文件。",
        "inputs": ["已确认 requirements"],
        "outputs": target_files,
        "dependencies": ["动态 step design contract"],
        "implementation_suggestions": ["按 contract 生成结构设计。"],
        "acceptance_notes": ["目标文件都有 file_design。"],
        "out_of_scope": [
            "不处理 lgwf-wf-prompt-fix。",
            "不修改 lgwf-wf-tools。",
            "不提供自动修复。",
            "不提供端到端运行保证。",
        ],
        "confirmation_points": ["确认阶段边界。"],
        "target_files": target_files,
        "target_dirs": target_dirs,
        "runtime_artifacts": [f".lgwf/{stage_id}_result.json"],
        "source_refs": ["step_design_validation_contract"],
        "risk_notes": ["阶段 workflow 必须来自 required_stage_workflows。"],
    }


def run_script(work_dir: Path, relative: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(WF_ROOT / relative)],
        cwd=work_dir,
        env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"},
        text=True,
        encoding="utf-8",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


class ProposalQualityGateTest(unittest.TestCase):
    def prepare_valid_step_design_proposal(self, work_dir: Path) -> dict:
        lgwf_dir = work_dir / ".lgwf"
        write_json(
            lgwf_dir / "create_requirements.json",
            {
                "confirmed": {
                    "workflow_id": "demo",
                    "workflow_name": "demo",
                    "target_package_root": "skills/demo",
                    "purpose": "创建 demo workflow。",
                }
            },
        )
        write_json(
            lgwf_dir / "business_flow.json",
            {
                "confirmed": {
                    "workflow_id": "demo",
                    "workflow_name": "demo",
                    "target_package_root": "skills/demo",
                    "business_goal": "运行 demo workflow。",
                    "stages": [
                        {
                            "stage_id": "prepare",
                            "objective": "准备输入并生成结果。",
                            "input_sources": [".lgwf/create_requirements.json"],
                            "outputs": [".lgwf/prepare_result.json"],
                            "key_nodes": ["run_agent", "run_script"],
                        }
                    ],
                }
            },
        )
        write_json(
            lgwf_dir / "scaffold_package_result.json",
            {
                "scaffold_plan": {
                    "workflow_name": "demo",
                    "target_package_root": "skills/demo",
                    "package_profile": "internal_workflow_package",
                    "stage_manifest": [
                        {
                            "stage_id": "prepare",
                            "stage_dir": "01_prepare",
                            "workflow_ref": "wf/01_prepare/workflow.lgwf",
                        }
                    ],
                    "create_dirs": [
                        "wf",
                        "wf/01_prepare",
                        "wf/01_prepare/agents",
                        "wf/01_prepare/scripts",
                        "tests",
                        "ws",
                    ],
                    "create_files": [
                        "AGENTS.md",
                        "README.md",
                        "entry_contract.json",
                        "wf/workflow.lgwf",
                        "wf/artifact_contracts.json",
                        "wf/01_prepare/workflow.lgwf",
                        "wf/01_prepare/agents/prompt.md",
                        "wf/01_prepare/scripts/run.py",
                        "tests/test_workflow_structure.py",
                    ],
                }
            },
        )
        for relative in (
            "03_confirm_step_designs/02_step_design_proposal/scripts/build_step_design_contract.py",
            "03_confirm_step_designs/02_step_design_proposal/scripts/generate_step_designs_proposal.py",
            "03_confirm_step_designs/02_step_design_proposal/scripts/normalize_step_designs_proposal.py",
        ):
            completed = run_script(work_dir, relative)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            if relative.endswith("build_step_design_contract.py"):
                self.assertTrue((lgwf_dir / "step_design_validation_contract.json").is_file())
                authoring_context = json.loads(
                    (lgwf_dir / "step_design_authoring_context.json").read_text(encoding="utf-8")
                )
                self.assertEqual(
                    "Bounded first-pass authoring context for .lgwf/step_designs_proposal.json.",
                    authoring_context["purpose"],
                )
                self.assertIn("required_stage_workflows", authoring_context)
        return json.loads((lgwf_dir / "step_designs_proposal.json").read_text(encoding="utf-8"))

    def test_business_flow_gate_passes_matching_current_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work_dir = Path(temp)
            lgwf_dir = work_dir / ".lgwf"
            write_json(
                lgwf_dir / "create_requirements.json",
                {"confirmed": {"workflow_name": "demo", "target_package_root": "skills/demo"}},
            )
            write_json(
                lgwf_dir / "business_flow_proposal.json",
                {
                    "workflow_id": "demo",
                    "workflow_name": "demo",
                    "target_package_root": "skills/demo",
                    "stages": [],
                },
            )

            completed = run_script(work_dir, "02_confirm_business_flow/01_business_flow_proposal/scripts/validate_proposal.py")

            self.assertEqual(completed.returncode, 0, completed.stderr)
            payload = json.loads(completed.stdout)
            result = payload["lgwf_wf_create.business_flow_proposal_quality_gate"]
            self.assertTrue(result["passed"])
            self.assertTrue((lgwf_dir / "business_flow_proposal_quality_gate.json").is_file())

    def test_requirements_gate_rejects_missing_proposal(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work_dir = Path(temp)
            lgwf_dir = work_dir / ".lgwf"
            write_json(lgwf_dir / "raw_intent_request.json", {"workflow_name": "demo"})

            completed = run_script(work_dir, "01_confirm_requirements/02_requirements_proposal/scripts/validate_proposal.py")

            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads((lgwf_dir / "create_requirements_proposal_quality_gate.json").read_text(encoding="utf-8"))
            self.assertFalse(result["passed"])
            self.assertIn("proposal_exists", [check["name"] for check in result["checks"] if not check["passed"]])

    def test_requirements_gate_treats_target_package_hint_as_reference_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work_dir = Path(temp)
            lgwf_dir = work_dir / ".lgwf"
            write_json(lgwf_dir / "raw_intent_request.json", {"target_package_hint": "demo workflow"})
            write_json(
                lgwf_dir / "create_requirements_proposal.json",
                {
                    "workflow_name": "demo",
                    "target_package_root": "skills/demo",
                    "requirements": [],
                },
            )

            completed = run_script(work_dir, "01_confirm_requirements/02_requirements_proposal/scripts/validate_proposal.py")

            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads((lgwf_dir / "create_requirements_proposal_quality_gate.json").read_text(encoding="utf-8"))
            self.assertTrue(result["passed"])
            self.assertEqual(result["expected_identity"]["target_package_root"], "")
            self.assertEqual(result["reference_hints"]["target_package_hint"], "demo workflow")

    def test_requirements_gate_requires_reference_package_source_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work_dir = Path(temp)
            lgwf_dir = work_dir / ".lgwf"
            reference_doc = work_dir / "repo-context-pack-goal-and-implementation.md"
            reference_doc.write_text(
                "\n".join(
                    [
                        "# repo-context-pack",
                        "- `SKILL.md` 是 skill 入口。",
                        "- `scripts/build_context_pack.py` 负责生成 context pack。",
                        "- `tests/test_build_context_pack.py` 覆盖构建脚本。",
                        "- `wf/shared/scripts/repo_context_runtime.py` 提供共享 runtime。",
                    ]
                ),
                encoding="utf-8",
            )
            write_json(
                lgwf_dir / "raw_intent_request.json",
                {
                    "workflow_name": "repo-context-pack",
                    "target_package_root": "skills/repo-context-pack",
                    "request": {"target_file": str(reference_doc)},
                },
            )
            write_json(
                lgwf_dir / "create_requirements_proposal.json",
                {
                    "workflow_name": "repo-context-pack",
                    "target_package_root": "skills/repo-context-pack",
                    "purpose": "生成 repo context pack skill。",
                    "expected_inputs": ["仓库路径"],
                    "expected_outputs": ["SKILL.md", "直接脚本入口、workflow 定义和最小测试"],
                    "reference_sources": [str(reference_doc)],
                },
            )

            completed = run_script(work_dir, "01_confirm_requirements/02_requirements_proposal/scripts/validate_proposal.py")

            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads((lgwf_dir / "create_requirements_proposal_quality_gate.json").read_text(encoding="utf-8"))
            self.assertFalse(result["passed"])
            self.assertEqual(
                result["semantic_required_package_files"],
                [
                    "SKILL.md",
                    "scripts/build_context_pack.py",
                    "tests/test_build_context_pack.py",
                    "wf/shared/scripts/repo_context_runtime.py",
                ],
            )
            failures = {check["name"]: check["message"] for check in result["checks"] if not check["passed"]}
            self.assertIn("semantic_package_file_preserved_scripts_build_context_pack_py", failures)
            self.assertIn("scripts/build_context_pack.py", failures["semantic_package_file_preserved_scripts_build_context_pack_py"])
            self.assertIn("semantic_package_file_preserved_tests_test_build_context_pack_py", failures)
            self.assertIn("semantic_package_file_preserved_wf_shared_scripts_repo_context_runtime_py", failures)

    def test_requirements_gate_accepts_preserved_reference_package_source_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work_dir = Path(temp)
            lgwf_dir = work_dir / ".lgwf"
            reference_doc = work_dir / "repo-context-pack-goal-and-implementation.md"
            reference_doc.write_text(
                "\n".join(
                    [
                        "# repo-context-pack",
                        "- `SKILL.md` 是 skill 入口。",
                        "- `scripts/build_context_pack.py` 负责生成 context pack。",
                        "- `tests/test_build_context_pack.py` 覆盖构建脚本。",
                        "- `wf/shared/scripts/repo_context_runtime.py` 提供共享 runtime。",
                    ]
                ),
                encoding="utf-8",
            )
            write_json(
                lgwf_dir / "raw_intent_request.json",
                {
                    "workflow_name": "repo-context-pack",
                    "target_package_root": "skills/repo-context-pack",
                    "request": {"target_file": str(reference_doc)},
                },
            )
            write_json(
                lgwf_dir / "create_requirements_proposal.json",
                {
                    "workflow_name": "repo-context-pack",
                    "target_package_root": "skills/repo-context-pack",
                    "purpose": "生成 repo context pack skill。",
                    "expected_inputs": ["仓库路径"],
                    "expected_outputs": ["生成 `SKILL.md`、workflow 定义和 context pack 文件"],
                    "package_source_files": [
                        "SKILL.md",
                        "scripts/build_context_pack.py",
                        "tests/test_build_context_pack.py",
                        "wf/shared/scripts/repo_context_runtime.py",
                    ],
                    "reference_sources": [str(reference_doc)],
                },
            )

            completed = run_script(work_dir, "01_confirm_requirements/02_requirements_proposal/scripts/validate_proposal.py")

            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads((lgwf_dir / "create_requirements_proposal_quality_gate.json").read_text(encoding="utf-8"))
            self.assertTrue(result["passed"])
            self.assertEqual(
                result["semantic_required_package_files"],
                [
                    "SKILL.md",
                    "scripts/build_context_pack.py",
                    "tests/test_build_context_pack.py",
                    "wf/shared/scripts/repo_context_runtime.py",
                ],
            )

    def test_business_flow_gate_rejects_target_package_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work_dir = Path(temp)
            lgwf_dir = work_dir / ".lgwf"
            write_json(
                lgwf_dir / "create_requirements.json",
                {"confirmed": {"workflow_name": "demo", "target_package_root": "skills/demo"}},
            )
            write_json(
                lgwf_dir / "business_flow_proposal.json",
                {
                    "workflow_name": "demo",
                    "target_package_root": "skills/old-demo",
                    "stages": [],
                },
            )

            completed = run_script(work_dir, "02_confirm_business_flow/01_business_flow_proposal/scripts/validate_proposal.py")

            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads((lgwf_dir / "business_flow_proposal_quality_gate.json").read_text(encoding="utf-8"))
            self.assertFalse(result["passed"])
            failures = {check["name"]: check["message"] for check in result["checks"] if not check["passed"]}
            self.assertIn("target_package_root_matches", failures)
            self.assertIn("skills/old-demo", failures["target_package_root_matches"])

    def test_business_flow_assert_quality_gate_rejects_failed_react_result(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work_dir = Path(temp)
            lgwf_dir = work_dir / ".lgwf"
            write_json(
                lgwf_dir / "business_flow_proposal_quality_gate.json",
                {
                    "passed": False,
                    "checks": [
                        {
                            "name": "target_package_root_matches",
                            "passed": False,
                            "message": "target_package_root 不一致",
                        }
                    ],
                },
            )

            completed = run_script(
                work_dir,
                "02_confirm_business_flow/01_business_flow_proposal/scripts/assert_quality_gate.py",
            )

            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("business flow proposal quality gate failed", completed.stderr)

    def test_step_design_gate_rejects_stale_proposal(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work_dir = Path(temp)
            lgwf_dir = work_dir / ".lgwf"
            write_json(
                lgwf_dir / "step_designs_proposal.json",
                {
                    "workflow_name": "demo",
                    "target_package_root": "skills/demo",
                    "step_designs": [],
                },
            )
            write_json(
                lgwf_dir / "scaffold_package_result.json",
                {"scaffold_plan": {"workflow_name": "demo", "target_package_root": "skills/demo"}},
            )
            os.utime(lgwf_dir / "step_designs_proposal.json", (1000, 1000))
            os.utime(lgwf_dir / "scaffold_package_result.json", (2000, 2000))

            completed = run_script(
                work_dir,
                "03_confirm_step_designs/02_step_design_proposal/scripts/validate_step_designs_structure.py",
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads((lgwf_dir / "step_design_structural_gate.json").read_text(encoding="utf-8"))
            self.assertFalse(result["passed"])
            self.assertIn("proposal_fresh_enough", [check["name"] for check in result["checks"] if not check["passed"]])

    def test_step_design_gate_rejects_doc_path_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work_dir = Path(temp)
            lgwf_dir = work_dir / ".lgwf"
            write_json(
                lgwf_dir / "business_flow.json",
                {
                    "confirmed": {
                        "workflow_name": "demo",
                        "target_package_root": "skills/demo",
                        "stages": [{"stage_id": "prepare"}],
                    }
                },
            )
            write_json(
                lgwf_dir / "create_requirements.json",
                {"confirmed": {"workflow_name": "demo", "target_package_root": "skills/demo"}},
            )
            write_json(
                lgwf_dir / "scaffold_package_result.json",
                {
                    "scaffold_plan": {
                        "workflow_name": "demo",
                        "target_package_root": "skills/demo",
                        "stage_manifest": [{"stage_id": "prepare", "stage_dir": "01_prepare"}],
                    }
                },
            )
            write_json(
                lgwf_dir / "step_designs_proposal.json",
                {
                    "workflow_id": "demo",
                    "workflow_name": "demo",
                    "target_package_root": "skills/demo",
                    "step_designs": [
                        {
                            "step_slug": "prepare",
                            "step_name": "准备",
                            "stage_id": "prepare",
                            "goal": "准备目标 workflow。",
                            "inputs": ["需求"],
                            "outputs": ["wf/01_prepare/workflow.lgwf"],
                            "dependencies": ["需求确认"],
                            "implementation_suggestions": ["生成阶段 workflow。"],
                            "acceptance_notes": ["阶段 workflow 存在。"],
                            "out_of_scope": ["端到端运行保证"],
                            "confirmation_points": ["阶段边界"],
                            "doc_path": "docs/steps/prepare.md",
                        }
                    ],
                },
            )

            completed = run_script(
                work_dir,
                "03_confirm_step_designs/02_step_design_proposal/scripts/validate_step_designs_structure.py",
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads((lgwf_dir / "step_design_structural_gate.json").read_text(encoding="utf-8"))
            self.assertFalse(result["passed"])
            failures = {check["name"]: check["message"] for check in result["checks"] if not check["passed"]}
            self.assertIn("step_designs[0]_doc_path_not_used", failures)

    def test_step_design_structural_gate_requires_source_refs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work_dir = Path(temp)
            lgwf_dir = work_dir / ".lgwf"
            write_json(
                lgwf_dir / "business_flow.json",
                {
                    "confirmed": {
                        "workflow_name": "demo",
                        "target_package_root": "skills/demo",
                        "stages": [{"stage_id": "prepare"}],
                    }
                },
            )
            write_json(
                lgwf_dir / "create_requirements.json",
                {"confirmed": {"workflow_name": "demo", "target_package_root": "skills/demo"}},
            )
            write_json(
                lgwf_dir / "scaffold_package_result.json",
                {
                    "scaffold_plan": {
                        "workflow_name": "demo",
                        "target_package_root": "skills/demo",
                        "stage_manifest": [{"stage_id": "prepare", "stage_dir": "01_prepare"}],
                    }
                },
            )
            write_json(
                lgwf_dir / "step_designs_proposal.json",
                {
                    "workflow_id": "demo",
                    "workflow_name": "demo",
                    "target_package_root": "skills/demo",
                    "step_designs": [
                        {
                            "step_slug": "prepare",
                            "step_name": "准备",
                            "stage_id": "prepare",
                            "goal": "准备目标 workflow。",
                            "inputs": ["需求"],
                            "outputs": ["wf/01_prepare/workflow.lgwf"],
                            "dependencies": ["需求确认"],
                            "implementation_suggestions": ["生成阶段 workflow。"],
                            "acceptance_notes": ["阶段 workflow 存在。"],
                            "out_of_scope": ["端到端运行保证"],
                            "confirmation_points": ["阶段边界"],
                        }
                    ],
                },
            )

            completed = run_script(
                work_dir,
                "03_confirm_step_designs/02_step_design_proposal/scripts/validate_step_designs_structure.py",
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads((lgwf_dir / "step_design_structural_gate.json").read_text(encoding="utf-8"))
            self.assertFalse(result["passed"])
            failures = {check["name"]: check["message"] for check in result["checks"] if not check["passed"]}
            self.assertIn("step_designs[0]_source_refs_present", failures)
            observation = json.loads((lgwf_dir / "step_design_observation.json").read_text(encoding="utf-8"))
            self.assertFalse(observation["passed"])
            self.assertEqual(observation["verdict"], "revise")
            self.assertIn("step_designs[0]_source_refs_present", observation["issue_signatures"])
            self.assertIn(
                "step_designs[0].source_refs 必须是非空数组",
                json.dumps(observation["reason_feedback"], ensure_ascii=False),
            )
            self.assertNotIn("valid_parts_to_preserve", observation)

    def test_step_design_validator_rejects_missing_exact_content_and_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work_dir = Path(temp)
            lgwf_dir = work_dir / ".lgwf"
            proposal = self.prepare_valid_step_design_proposal(work_dir)
            for item in proposal["file_designs"]:
                if item.get("path") == "wf/01_prepare/agents/prompt.md":
                    item.pop("exact_content", None)
                if item.get("path") == "wf/01_prepare/scripts/run.py":
                    item.pop("script_contract", None)
            write_json(lgwf_dir / "step_designs_proposal.json", proposal)

            completed = run_script(
                work_dir,
                "03_confirm_step_designs/02_step_design_proposal/scripts/validate_step_designs_structure.py",
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads((lgwf_dir / "step_design_structural_gate.json").read_text(encoding="utf-8"))
            self.assertFalse(result["passed"])
            failure_text = json.dumps([check for check in result["checks"] if not check["passed"]], ensure_ascii=False)
            self.assertIn("必须提供 exact_content", failure_text)
            self.assertIn("必须提供 script_contract", failure_text)

    def test_step_design_validator_rejects_placeholder_and_generic_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work_dir = Path(temp)
            lgwf_dir = work_dir / ".lgwf"
            proposal = self.prepare_valid_step_design_proposal(work_dir)
            for item in proposal["file_designs"]:
                if item.get("path") == "wf/01_prepare/agents/prompt.md":
                    item["exact_content"] = f'{item["exact_content"]}\nTODO placeholder_result\n'
                if item.get("path") == "wf/01_prepare/scripts/run.py":
                    item["script_contract"]["behavior"] = "待实现 generated_result"
            write_json(lgwf_dir / "step_designs_proposal.json", proposal)

            completed = run_script(
                work_dir,
                "03_confirm_step_designs/02_step_design_proposal/scripts/validate_step_designs_structure.py",
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads((lgwf_dir / "step_design_structural_gate.json").read_text(encoding="utf-8"))
            self.assertFalse(result["passed"])
            failure_text = json.dumps([check for check in result["checks"] if not check["passed"]], ensure_ascii=False)
            for term in ("TODO", "placeholder_result", "generated_result", "待实现"):
                self.assertIn(term, failure_text)

    def test_step_design_normalizer_does_not_fill_semantic_fallback_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work_dir = Path(temp)
            lgwf_dir = work_dir / ".lgwf"
            write_json(
                lgwf_dir / "step_design_validation_contract.json",
                {
                    "identity": {
                        "workflow_id": "demo",
                        "workflow_name": "demo",
                        "target_package_root": "skills/demo",
                        "package_profile": "internal_workflow_package",
                    },
                    "stage_identity": {"canonical_stage_ids": ["prepare"], "stage_aliases": {}},
                    "required_stage_workflows": [
                        {
                            "stage_id": "prepare",
                            "workflow_ref": "wf/01_prepare/workflow.lgwf",
                            "aliases": [],
                        }
                    ],
                    "required_file_designs": [
                        "wf/01_prepare/workflow.lgwf",
                        "wf/01_prepare/agents/prompt.md",
                        "wf/01_prepare/scripts/run.py",
                    ],
                },
            )
            write_json(
                lgwf_dir / "step_designs_proposal.json",
                {
                    "workflow_id": "demo",
                    "workflow_name": "demo",
                    "target_package_root": "skills/demo",
                    "package_profile": "internal_workflow_package",
                    "directory_designs": [],
                    "step_designs": [],
                    "file_designs": [
                        {"path": "wf/01_prepare/workflow.lgwf", "kind": "lgwf_workflow"},
                        {"path": "wf/01_prepare/agents/prompt.md", "kind": "prompt"},
                        {"path": "wf/01_prepare/scripts/run.py", "kind": "python_script"},
                    ],
                },
            )

            completed = run_script(
                work_dir,
                "03_confirm_step_designs/02_step_design_proposal/scripts/normalize_step_designs_proposal.py",
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            proposal = json.loads((lgwf_dir / "step_designs_proposal.json").read_text(encoding="utf-8"))
            by_path = {item["path"]: item for item in proposal["file_designs"]}
            self.assertEqual(by_path["wf/01_prepare/workflow.lgwf"]["content_mode"], "exact")
            self.assertEqual(by_path["wf/01_prepare/agents/prompt.md"]["content_mode"], "exact")
            self.assertEqual(by_path["wf/01_prepare/scripts/run.py"]["content_mode"], "contract")
            self.assertNotIn("exact_content", by_path["wf/01_prepare/workflow.lgwf"])
            self.assertNotIn("exact_content", by_path["wf/01_prepare/agents/prompt.md"])
            self.assertNotIn("script_contract", by_path["wf/01_prepare/scripts/run.py"])

    def test_step_design_normalizer_does_not_define_design_synthesis_helpers(self) -> None:
        script = (
            WF_ROOT
            / "03_confirm_step_designs/02_step_design_proposal/scripts/normalize_step_designs_proposal.py"
        ).read_text(encoding="utf-8")
        for forbidden in (
            "ensure_required_file_designs",
            "ensure_required_stage_steps",
            "ensure_directory_designs_for_targets",
            "ensure_all_designs_referenced",
            "fallback_exact_workflow",
            "created_fallback_step_design",
        ):
            self.assertNotIn(forbidden, script)

    def test_step_design_normalizer_leaves_required_design_gaps_for_validator(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work_dir = Path(temp)
            lgwf_dir = work_dir / ".lgwf"
            write_json(
                lgwf_dir / "create_requirements.json",
                {"confirmed": {"workflow_id": "demo", "workflow_name": "demo", "target_package_root": "skills/demo"}},
            )
            write_json(
                lgwf_dir / "business_flow.json",
                {
                    "confirmed": {
                        "workflow_id": "demo",
                        "workflow_name": "demo",
                        "target_package_root": "skills/demo",
                        "stages": [{"stage_id": "prepare"}],
                    }
                },
            )
            write_json(
                lgwf_dir / "scaffold_package_result.json",
                {
                    "scaffold_plan": {
                        "workflow_name": "demo",
                        "target_package_root": "skills/demo",
                        "stage_manifest": [
                            {
                                "stage_id": "prepare",
                                "stage_dir": "01_prepare",
                                "workflow_ref": "wf/01_prepare/workflow.lgwf",
                            }
                        ],
                        "create_files": ["wf/01_prepare/workflow.lgwf"],
                    }
                },
            )
            write_json(
                lgwf_dir / "step_design_validation_contract.json",
                {
                    "identity": {
                        "workflow_id": "demo",
                        "workflow_name": "demo",
                        "target_package_root": "skills/demo",
                        "package_profile": "internal_workflow_package",
                    },
                    "stage_identity": {"canonical_stage_ids": ["prepare"], "stage_aliases": {}},
                    "required_stage_workflows": [
                        {
                            "stage_id": "prepare",
                            "workflow_ref": "wf/01_prepare/workflow.lgwf",
                            "aliases": [],
                        }
                    ],
                    "required_file_designs": ["wf/01_prepare/workflow.lgwf"],
                    "scaffold_create_files": ["wf/01_prepare/workflow.lgwf"],
                },
            )
            write_json(
                lgwf_dir / "step_designs_proposal.json",
                {
                    "workflow_id": "demo",
                    "workflow_name": "demo",
                    "target_package_root": "skills/demo",
                    "package_profile": "internal_workflow_package",
                    "source_business_flow_stages": ["prepare"],
                    "directory_designs": [],
                    "file_designs": [],
                    "step_designs": [valid_step("prepare", ["README.md"], ["."])],
                    "design_rationale": ["故意缺失 required design，验证 normalize 不兜底。"],
                },
            )

            normalize = run_script(
                work_dir,
                "03_confirm_step_designs/02_step_design_proposal/scripts/normalize_step_designs_proposal.py",
            )
            self.assertEqual(normalize.returncode, 0, normalize.stderr)
            proposal = json.loads((lgwf_dir / "step_designs_proposal.json").read_text(encoding="utf-8"))
            self.assertEqual([], proposal["file_designs"])
            self.assertNotIn("wf/01_prepare/workflow.lgwf", proposal["step_designs"][0]["target_files"])

            validate = run_script(
                work_dir,
                "03_confirm_step_designs/02_step_design_proposal/scripts/validate_step_designs_structure.py",
            )

            self.assertEqual(validate.returncode, 0, validate.stderr)
            result = json.loads((lgwf_dir / "step_design_structural_gate.json").read_text(encoding="utf-8"))
            self.assertFalse(result["passed"])
            failures = {check["name"] for check in result["checks"] if not check["passed"]}
            self.assertIn("required_file_design_present_wf/01_prepare/workflow.lgwf", failures)
            self.assertIn("required_file_design_referenced_wf/01_prepare/workflow.lgwf", failures)
            self.assertIn("stage_workflow_target_file_present_prepare", failures)
            observation = json.loads((lgwf_dir / "step_design_observation.json").read_text(encoding="utf-8"))
            feedback_text = json.dumps(observation["reason_feedback"], ensure_ascii=False)
            self.assertIn("required_file_design_present_wf/01_prepare/workflow.lgwf", feedback_text)
            self.assertEqual("targeted_repair", observation["reason_feedback"]["repair_mode"])
            initial_decision = json.loads((lgwf_dir / "step_designs_proposal_decision.json").read_text(encoding="utf-8"))
            self.assertEqual("python_decide_step_designs", initial_decision["source"])

            decide = run_script(
                work_dir,
                "03_confirm_step_designs/02_step_design_proposal/scripts/decide_step_designs.py",
            )
            self.assertEqual(decide.returncode, 0, decide.stderr)
            repeated_decision = json.loads(
                (lgwf_dir / "step_designs_proposal_decision.json").read_text(encoding="utf-8")
            )
            self.assertTrue(repeated_decision["no_progress_risk"])
            self.assertIn(
                "required_file_design_present_wf/01_prepare/workflow.lgwf",
                repeated_decision["repeat_issue_signatures"],
            )

    def test_step_design_contract_prefers_scaffold_workflows_over_business_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work_dir = Path(temp)
            lgwf_dir = work_dir / ".lgwf"
            write_json(
                lgwf_dir / "business_flow.json",
                {
                    "confirmed": {
                        "workflow_name": "demo",
                        "target_package_root": "skills/demo",
                        "stages": [{"stage_id": "prepare"}, {"stage_id": "run_checks"}],
                    }
                },
            )
            write_json(
                lgwf_dir / "create_requirements.json",
                {"confirmed": {"workflow_name": "demo", "target_package_root": "skills/demo"}},
            )
            write_json(
                lgwf_dir / "scaffold_package_result.json",
                {
                    "scaffold_plan": {
                        "workflow_name": "demo",
                        "target_package_root": "skills/demo",
                        "stage_manifest": [
                            {"stage_id": "prepare", "stage_dir": "01_prepare"},
                            {"stage_id": "run_checks", "stage_dir": "02_run_checks"},
                        ],
                    }
                },
            )

            completed = run_script(
                work_dir,
                "03_confirm_step_designs/02_step_design_proposal/scripts/build_step_design_contract.py",
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            contract = json.loads((lgwf_dir / "step_design_validation_contract.json").read_text(encoding="utf-8"))
            workflow_refs = [item["workflow_ref"] for item in contract["required_stage_workflows"]]
            self.assertEqual(workflow_refs, ["wf/01_prepare/workflow.lgwf", "wf/02_run_checks/workflow.lgwf"])
            self.assertNotIn("wf/prepare/workflow.lgwf", workflow_refs)
            self.assertEqual(contract["stage_identity"]["stage_aliases"]["01_prepare"], "prepare")

    def test_step_design_gate_rejects_extra_noncanonical_stage_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work_dir = Path(temp)
            lgwf_dir = work_dir / ".lgwf"
            write_json(
                lgwf_dir / "business_flow.json",
                {
                    "confirmed": {
                        "workflow_name": "demo",
                        "target_package_root": "skills/demo",
                        "stages": [{"stage_id": "prepare"}],
                    }
                },
            )
            write_json(
                lgwf_dir / "create_requirements.json",
                {"confirmed": {"workflow_name": "demo", "target_package_root": "skills/demo"}},
            )
            write_json(
                lgwf_dir / "scaffold_package_result.json",
                {
                    "scaffold_plan": {
                        "workflow_name": "demo",
                        "target_package_root": "skills/demo",
                        "stage_manifest": [{"stage_id": "prepare", "stage_dir": "01_prepare"}],
                    }
                },
            )
            completed = run_script(
                work_dir,
                "03_confirm_step_designs/02_step_design_proposal/scripts/build_step_design_contract.py",
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            target_files = [
                "AGENTS.md",
                "README.md",
                "entry_contract.json",
                "wf/workflow.lgwf",
                "wf/artifact_contracts.json",
                "wf/01_prepare/workflow.lgwf",
                "wf/prepare/workflow.lgwf",
            ]
            target_dirs = ["wf", "wf/01_prepare", "wf/prepare"]
            write_json(
                lgwf_dir / "step_designs_proposal.json",
                {
                    "workflow_id": "demo",
                    "workflow_name": "demo",
                    "target_package_root": "skills/demo",
                    "package_profile": "internal_workflow_package",
                    "source_business_flow_stages": ["prepare"],
                    "directory_designs": [
                        design_for_dir("wf", ["wf/workflow.lgwf", "wf/artifact_contracts.json"]),
                        design_for_dir("wf/01_prepare", ["wf/01_prepare/workflow.lgwf"]),
                        design_for_dir("wf/prepare", ["wf/prepare/workflow.lgwf"]),
                    ],
                    "file_designs": [design_for_file(path) for path in target_files],
                    "step_designs": [valid_step("prepare", target_files, target_dirs)],
                    "design_rationale": ["测试额外非 canonical workflow 会被拒绝。"],
                },
            )

            completed = run_script(
                work_dir,
                "03_confirm_step_designs/02_step_design_proposal/scripts/validate_step_designs_structure.py",
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads((lgwf_dir / "step_design_structural_gate.json").read_text(encoding="utf-8"))
            self.assertFalse(result["passed"])
            failures = {check["name"]: check["message"] for check in result["checks"] if not check["passed"]}
            self.assertIn("stage_workflow_target_file_allowed_wf/prepare/workflow.lgwf", failures)

    def test_deterministic_step_design_generator_passes_structural_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work_dir = Path(temp)
            lgwf_dir = work_dir / ".lgwf"
            write_json(
                lgwf_dir / "business_flow.json",
                {
                    "confirmed": {
                        "workflow_id": "demo",
                        "workflow_name": "demo",
                        "target_package_root": "skills/demo",
                        "business_goal": "生成 demo workflow package。",
                        "stages": [
                            {
                                "stage_id": "prepare",
                                "objective": "准备输入上下文。",
                                "input_sources": ["入口 JSON"],
                                "outputs": [".lgwf/prepare_result.json"],
                            },
                            {
                                "stage_id": "render",
                                "objective": "渲染最终摘要。",
                                "depends_on": ["prepare"],
                                "input_sources": [".lgwf/prepare_result.json"],
                                "outputs": ["reports/demo/report.md"],
                            },
                        ],
                    }
                },
            )
            write_json(
                lgwf_dir / "create_requirements.json",
                {
                    "confirmed": {
                        "workflow_id": "demo",
                        "workflow_name": "demo",
                        "target_package_root": "skills/demo",
                        "purpose": "生成 demo workflow package。",
                    }
                },
            )
            write_json(
                lgwf_dir / "scaffold_package_result.json",
                {
                    "scaffold_plan": {
                        "workflow_name": "demo",
                        "target_package_root": "skills/demo",
                        "package_profile": "internal_workflow_package",
                        "stage_manifest": [
                            {
                                "stage_id": "prepare",
                                "stage_dir": "01_prepare",
                                "workflow_ref": "wf/01_prepare/workflow.lgwf",
                            },
                            {
                                "stage_id": "render",
                                "stage_dir": "02_render",
                                "workflow_ref": "wf/02_render/workflow.lgwf",
                            },
                        ],
                        "create_dirs": [
                            "wf",
                            "wf/01_prepare",
                            "wf/01_prepare/agents",
                            "wf/01_prepare/scripts",
                            "wf/02_render",
                            "wf/02_render/scripts",
                            "tests",
                            "ws",
                        ],
                        "create_files": [
                            "AGENTS.md",
                            "README.md",
                            "entry_contract.json",
                            "wf/workflow.lgwf",
                            "wf/artifact_contracts.json",
                            "wf/01_prepare/workflow.lgwf",
                            "wf/01_prepare/agents/prompt.md",
                            "wf/01_prepare/scripts/run.py",
                            "wf/02_render/workflow.lgwf",
                            "wf/02_render/scripts/run.py",
                            "tests/test_workflow_structure.py",
                        ],
                    }
                },
            )
            for relative in (
                "03_confirm_step_designs/02_step_design_proposal/scripts/build_step_design_contract.py",
                "03_confirm_step_designs/02_step_design_proposal/scripts/generate_step_designs_proposal.py",
                "03_confirm_step_designs/02_step_design_proposal/scripts/normalize_step_designs_proposal.py",
                "03_confirm_step_designs/02_step_design_proposal/scripts/validate_step_designs_structure.py",
            ):
                completed = run_script(work_dir, relative)
                self.assertEqual(completed.returncode, 0, completed.stderr)

            proposal = json.loads((lgwf_dir / "step_designs_proposal.json").read_text(encoding="utf-8"))
            result = json.loads((lgwf_dir / "step_design_structural_gate.json").read_text(encoding="utf-8"))
            self.assertTrue(result["passed"])
            file_paths = {item["path"] for item in proposal["file_designs"]}
            by_path = {item["path"]: item for item in proposal["file_designs"]}
            self.assertIn("tests/test_workflow_structure.py", file_paths)
            self.assertEqual(by_path["wf/workflow.lgwf"]["content_mode"], "exact")
            self.assertIn('WORKFLOW "01_prepare/workflow.lgwf"', by_path["wf/workflow.lgwf"]["exact_content"])
            self.assertEqual(by_path["wf/01_prepare/workflow.lgwf"]["content_mode"], "exact")
            self.assertIn("CODEX run_agent", by_path["wf/01_prepare/workflow.lgwf"]["exact_content"])
            self.assertIn('PROMPT "agents/prompt.md"', by_path["wf/01_prepare/workflow.lgwf"]["exact_content"])
            self.assertIn('SCRIPT "scripts/run.py"', by_path["wf/01_prepare/workflow.lgwf"]["exact_content"])
            self.assertEqual(by_path["wf/01_prepare/agents/prompt.md"]["content_mode"], "exact")
            self.assertEqual(by_path["wf/01_prepare/scripts/run.py"]["content_mode"], "contract")
            self.assertEqual(by_path["wf/01_prepare/scripts/run.py"]["script_contract"]["entrypoint"], "main()")
            self.assertIn(
                ".lgwf/prepare_prompt_result.json",
                by_path["wf/01_prepare/scripts/run.py"]["script_contract"]["input_files"],
            )
            self.assertEqual(by_path["tests/test_workflow_structure.py"]["kind"], "test")
            self.assertIn("test_contract", by_path["tests/test_workflow_structure.py"])
            root_artifact_contract = by_path["wf/artifact_contracts.json"]["json_contract"]
            self.assertNotIn(".lgwf/package_contracts_result.json", root_artifact_contract["final_outputs"])
            self.assertIn("reports/demo/report.md", root_artifact_contract["final_outputs"])
            self.assertIn(".lgwf/prepare_result.json", root_artifact_contract["script_writes"])
            target_files = {
                path
                for step in proposal["step_designs"]
                for path in step["target_files"]
            }
            self.assertIn("wf/01_prepare/workflow.lgwf", target_files)
            self.assertIn("wf/02_render/workflow.lgwf", target_files)
            self.assertNotIn("wf/prepare/workflow.lgwf", target_files)

    def test_step_design_pipeline_preserves_skill_wrapped_semantic_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work_dir = Path(temp)
            lgwf_dir = work_dir / ".lgwf"
            write_json(
                lgwf_dir / "create_requirements.json",
                {
                    "confirmed": {
                        "workflow_id": "repo-context-pack",
                        "workflow_name": "repo-context-pack",
                        "target_package_root": "skills/repo-context-pack",
                        "purpose": "创建一个名为 repo-context-pack 的 Codex skill，内嵌 LGWF workflow。",
                        "expected_outputs": [
                            "目标 package 包含 SKILL.md、AGENTS.md、README.md、entry_contract.json、scripts/build_context_pack.py、tests/test_build_context_pack.py、ws/ 和 wf/。",
                            "内嵌根 workflow 固定为 wf/workflow.lgwf，并包含 wf/artifact_contracts.json。",
                            "跨阶段可复用的纯函数放在 wf/shared/scripts/repo_context_runtime.py。",
                        ],
                    }
                },
            )
            write_json(
                lgwf_dir / "business_flow.json",
                {
                    "confirmed": {
                        "workflow_id": "repo-context-pack",
                        "workflow_name": "repo-context-pack",
                        "target_package_root": "skills/repo-context-pack",
                        "business_goal": "生成 repo context pack。",
                        "stages": [
                            {
                                "stage_id": "entry_scope_resolution",
                                "objective": "归一化入口请求。",
                                "input_sources": ["input JSON"],
                                "outputs": [".lgwf/repo_context_pack_request.json"],
                            },
                            {
                                "stage_id": "target_context_inventory",
                                "objective": "只读盘点目标目录。",
                                "depends_on": ["entry_scope_resolution"],
                                "input_sources": [".lgwf/repo_context_pack_request.json"],
                                "outputs": [".lgwf/context_inventory.json"],
                            },
                        ],
                    }
                },
            )
            for relative in (
                "02_confirm_business_flow/03_scaffold_package/scripts/scaffold_package.py",
                "03_confirm_step_designs/02_step_design_proposal/scripts/build_step_design_contract.py",
                "03_confirm_step_designs/02_step_design_proposal/scripts/generate_step_designs_proposal.py",
                "03_confirm_step_designs/02_step_design_proposal/scripts/normalize_step_designs_proposal.py",
                "03_confirm_step_designs/02_step_design_proposal/scripts/validate_step_designs_structure.py",
            ):
                completed = run_script(work_dir, relative)
                self.assertEqual(completed.returncode, 0, completed.stderr)

            scaffold = json.loads((lgwf_dir / "scaffold_package_result.json").read_text(encoding="utf-8"))
            plan = scaffold["scaffold_plan"]
            self.assertEqual(plan["package_profile"], "skill_wrapped_workflow")
            self.assertNotIn("wf/01_entry_scope_resolution/agents/prompt.md", plan["create_files"])
            self.assertNotIn("wf/01_entry_scope_resolution/resources/README.md", plan["create_files"])

            proposal = json.loads((lgwf_dir / "step_designs_proposal.json").read_text(encoding="utf-8"))
            result = json.loads((lgwf_dir / "step_design_structural_gate.json").read_text(encoding="utf-8"))
            self.assertTrue(result["passed"])
            file_paths = {item["path"] for item in proposal["file_designs"]}
            by_path = {item["path"]: item for item in proposal["file_designs"]}
            target_files = {
                path
                for step in proposal["step_designs"]
                for path in step["target_files"]
            }
            for path in (
                "SKILL.md",
                "scripts/build_context_pack.py",
                "tests/test_build_context_pack.py",
                "wf/shared/scripts/repo_context_runtime.py",
            ):
                self.assertIn(path, file_paths)
                self.assertIn(path, target_files)
            self.assertEqual(by_path["wf/workflow.lgwf"]["content_mode"], "exact")
            self.assertEqual(by_path["scripts/build_context_pack.py"]["content_mode"], "contract")
            self.assertIn("script_contract", by_path["scripts/build_context_pack.py"])

    def test_step_design_decide_writes_continue_until_observation_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work_dir = Path(temp)
            lgwf_dir = work_dir / ".lgwf"
            write_json(
                lgwf_dir / "step_design_observation.json",
                {
                    "passed": False,
                    "verdict": "revise",
                    "issue_signatures": ["stage_coverage.missing_prepare"],
                    "reason_feedback": {"repair_mode": "targeted_repair"},
                },
            )
            write_json(lgwf_dir / "step_designs_proposal_decision.json", {"issue_signatures": []})

            completed = run_script(
                work_dir,
                "03_confirm_step_designs/02_step_design_proposal/scripts/decide_step_designs.py",
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            payload = json.loads(completed.stdout)
            decision = json.loads((lgwf_dir / "step_designs_proposal_decision.json").read_text(encoding="utf-8"))
            analysis = json.loads((lgwf_dir / "step_design_decision_analysis.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["next"], "continue")
            self.assertEqual(decision["next"], "continue")
            self.assertEqual(analysis["recommended_next"], "continue")
            self.assertFalse(decision["passed"])

    def test_step_design_assert_quality_gate_rejects_failed_react_result(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work_dir = Path(temp)
            lgwf_dir = work_dir / ".lgwf"
            write_json(
                lgwf_dir / "step_design_observation.json",
                {
                    "passed": False,
                    "blocking_issues": [
                        {
                            "issue_id": "proposal_fresh_enough",
                            "evidence": "proposal 早于当前上游输入",
                            "required_change": "重新生成当前步骤设计 proposal",
                        }
                    ],
                },
            )

            completed = run_script(
                work_dir,
                "03_confirm_step_designs/02_step_design_proposal/scripts/assert_quality_gate.py",
            )

            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("step designs proposal quality gate failed", completed.stderr)


if __name__ == "__main__":
    unittest.main()
