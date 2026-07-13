# Step Design ReAct Slots Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `wf-create/wf/03_confirm_step_designs/02_step_design_proposal` 改造成四个 ReAct slot 都有 Codex 分析参与的高质量步骤设计生成链路，并让 `.lgwf/step_designs.json` 继续作为唯一确认后设计契约。

**Architecture:** `02_step_design_proposal/workflow.lgwf` 保持为阶段 proposal 子流程，但它的 `REACT step_design_proposal_react` 改为 `REASON/ACT/OBSERVE/DECIDE WORKFLOW` 四个 slot workflow。`OBSERVE` 先运行确定性 structural gate，再由 Codex 做 semantic audit，最后由脚本合并为 `.lgwf/step_design_observation.json`；下一轮 `REASON` 只消费该 observation 的 `reason_feedback` 生成修复策略。

**Tech Stack:** LGWF authoring DSL `REACT` / `WORKFLOW` slots, `CODEX` output JSON, Python 3 stdlib, `unittest`, existing `wf/shared/scripts/proposal_quality_gate.py` and confirmation helpers.

---

## File Structure

Modify:
- `skills/lgwf-wf-tools/workflows/wf-create/wf/03_confirm_step_designs/02_step_design_proposal/workflow.lgwf`：把 direct slot 改为 slot workflow 编排。
- `skills/lgwf-wf-tools/workflows/wf-create/wf/03_confirm_step_designs/02_step_design_proposal/README.md`：说明多一层 slot workflow 的必要性和状态边界。
- `skills/lgwf-wf-tools/workflows/wf-create/wf/03_confirm_step_designs/README.md`：更新产物列表和 OB -> REASON 反馈链路。
- `skills/lgwf-wf-tools/workflows/wf-create/wf/03_confirm_step_designs/workflow.lgwf`：更新 parent-visible artifact contract。
- `skills/lgwf-wf-tools/workflows/wf-create/wf/artifact_contracts.json`：登记新增 runtime artifacts。
- `skills/lgwf-wf-tools/workflows/wf-create/wf/04_implement_steps_react/01_implement_units/01_implement_one_unit/resources/codex_output_schemas.json`：登记新增 Codex JSON 输出 schema。
- `skills/lgwf-wf-tools/workflows/wf-create/tests/test_workflow_integrity.py`
- `skills/lgwf-wf-tools/workflows/wf-create/tests/test_prompt_contracts.py`
- `skills/lgwf-wf-tools/workflows/wf-create/tests/test_proposal_quality_gate.py`
- `skills/lgwf-wf-tools/workflows/wf-create/tests/test_structured_contracts.py`

Create:
- `skills/lgwf-wf-tools/workflows/wf-create/wf/03_confirm_step_designs/02_step_design_proposal/01_reason_step_designs/workflow.lgwf`
- `skills/lgwf-wf-tools/workflows/wf-create/wf/03_confirm_step_designs/02_step_design_proposal/01_reason_step_designs/README.md`
- `skills/lgwf-wf-tools/workflows/wf-create/wf/03_confirm_step_designs/02_step_design_proposal/01_reason_step_designs/agents/reason_step_designs.md`
- `skills/lgwf-wf-tools/workflows/wf-create/wf/03_confirm_step_designs/02_step_design_proposal/02_act_step_designs/workflow.lgwf`
- `skills/lgwf-wf-tools/workflows/wf-create/wf/03_confirm_step_designs/02_step_design_proposal/02_act_step_designs/README.md`
- `skills/lgwf-wf-tools/workflows/wf-create/wf/03_confirm_step_designs/02_step_design_proposal/02_act_step_designs/agents/act_step_designs.md`
- `skills/lgwf-wf-tools/workflows/wf-create/wf/03_confirm_step_designs/02_step_design_proposal/03_observe_step_designs/workflow.lgwf`
- `skills/lgwf-wf-tools/workflows/wf-create/wf/03_confirm_step_designs/02_step_design_proposal/03_observe_step_designs/README.md`
- `skills/lgwf-wf-tools/workflows/wf-create/wf/03_confirm_step_designs/02_step_design_proposal/03_observe_step_designs/agents/observe_step_designs.md`
- `skills/lgwf-wf-tools/workflows/wf-create/wf/03_confirm_step_designs/02_step_design_proposal/03_observe_step_designs/scripts/validate_step_designs_structure.py`
- `skills/lgwf-wf-tools/workflows/wf-create/wf/03_confirm_step_designs/02_step_design_proposal/03_observe_step_designs/scripts/merge_step_design_observation.py`
- `skills/lgwf-wf-tools/workflows/wf-create/wf/03_confirm_step_designs/02_step_design_proposal/04_decide_step_designs/workflow.lgwf`
- `skills/lgwf-wf-tools/workflows/wf-create/wf/03_confirm_step_designs/02_step_design_proposal/04_decide_step_designs/README.md`
- `skills/lgwf-wf-tools/workflows/wf-create/wf/03_confirm_step_designs/02_step_design_proposal/04_decide_step_designs/agents/decide_step_designs.md`
- `skills/lgwf-wf-tools/workflows/wf-create/wf/03_confirm_step_designs/02_step_design_proposal/04_decide_step_designs/scripts/decide_step_designs.py`

Delete after tests are updated:
- `skills/lgwf-wf-tools/workflows/wf-create/wf/03_confirm_step_designs/02_step_design_proposal/agents/design_steps_react.md`
- `skills/lgwf-wf-tools/workflows/wf-create/wf/03_confirm_step_designs/02_step_design_proposal/scripts/prepare_react_context.py`
- `skills/lgwf-wf-tools/workflows/wf-create/wf/03_confirm_step_designs/02_step_design_proposal/scripts/validate_step_designs_proposal.py`
- `skills/lgwf-wf-tools/workflows/wf-create/wf/03_confirm_step_designs/02_step_design_proposal/scripts/decide_react.py`

Keep and modify:
- `skills/lgwf-wf-tools/workflows/wf-create/wf/03_confirm_step_designs/02_step_design_proposal/scripts/prepare_react_feedback.py`
- `skills/lgwf-wf-tools/workflows/wf-create/wf/03_confirm_step_designs/02_step_design_proposal/scripts/assert_quality_gate.py`

---

### Task 1: Update Failing Structural Tests

**Files:**
- Modify: `skills/lgwf-wf-tools/workflows/wf-create/tests/test_workflow_integrity.py`
- Modify: `skills/lgwf-wf-tools/workflows/wf-create/tests/test_prompt_contracts.py`
- Modify: `skills/lgwf-wf-tools/workflows/wf-create/tests/test_structured_contracts.py`

- [ ] **Step 1: Update expected files for step design proposal slot workflows**

In `test_workflow_integrity.py`, update `test_confirm_step_designs_files_are_grouped_by_business_flow` so `expected_files` includes the new slot workflow files and no longer expects the old single prompt/script layout:

```python
"02_step_design_proposal/01_reason_step_designs/workflow.lgwf",
"02_step_design_proposal/01_reason_step_designs/README.md",
"02_step_design_proposal/01_reason_step_designs/agents/reason_step_designs.md",
"02_step_design_proposal/02_act_step_designs/workflow.lgwf",
"02_step_design_proposal/02_act_step_designs/README.md",
"02_step_design_proposal/02_act_step_designs/agents/act_step_designs.md",
"02_step_design_proposal/03_observe_step_designs/workflow.lgwf",
"02_step_design_proposal/03_observe_step_designs/README.md",
"02_step_design_proposal/03_observe_step_designs/agents/observe_step_designs.md",
"02_step_design_proposal/03_observe_step_designs/scripts/validate_step_designs_structure.py",
"02_step_design_proposal/03_observe_step_designs/scripts/merge_step_design_observation.py",
"02_step_design_proposal/04_decide_step_designs/workflow.lgwf",
"02_step_design_proposal/04_decide_step_designs/README.md",
"02_step_design_proposal/04_decide_step_designs/agents/decide_step_designs.md",
"02_step_design_proposal/04_decide_step_designs/scripts/decide_step_designs.py",
```

Add these old locations to `old_locations`:

```python
"02_step_design_proposal/agents/design_steps_react.md",
"02_step_design_proposal/scripts/prepare_react_context.py",
"02_step_design_proposal/scripts/validate_step_designs_proposal.py",
"02_step_design_proposal/scripts/decide_react.py",
```

- [ ] **Step 2: Update workflow snippets for slot topology**

In `test_confirm_step_designs_subflows_declare_local_responsibilities`, replace the `step_design_proposal` snippets with:

```python
"PY prepare_step_design_proposal_react_feedback",
"REACT step_design_proposal_react",
"REASON WORKFLOW reason_step_designs",
"ACT WORKFLOW act_step_designs",
"OBSERVE WORKFLOW observe_step_designs",
"DECIDE WORKFLOW decide_step_designs",
"PY assert_step_designs_proposal_quality_gate",
'WORKFLOW "01_reason_step_designs/workflow.lgwf"',
'WORKFLOW "02_act_step_designs/workflow.lgwf"',
'WORKFLOW "03_observe_step_designs/workflow.lgwf"',
'WORKFLOW "04_decide_step_designs/workflow.lgwf"',
'READ workspace file ".lgwf/scaffold_package_result.json";',
```

- [ ] **Step 3: Update Codex node contract expectations**

In `test_prompt_contracts.py`, update `expected_nodes` in `test_all_codex_prompt_nodes_have_contract_boundary_coverage` to include:

```python
"03_confirm_step_designs/02_step_design_proposal/01_reason_step_designs/workflow.lgwf:reason_step_designs",
"03_confirm_step_designs/02_step_design_proposal/02_act_step_designs/workflow.lgwf:act_step_designs",
"03_confirm_step_designs/02_step_design_proposal/03_observe_step_designs/workflow.lgwf:observe_step_designs",
"03_confirm_step_designs/02_step_design_proposal/04_decide_step_designs/workflow.lgwf:decide_step_designs",
```

Remove:

```python
"03_confirm_step_designs/02_step_design_proposal/workflow.lgwf:act",
```

- [ ] **Step 4: Update output JSON schema registry expectations**

In `test_codex_output_json_files_have_schema_registry_entries`, extend expected `output_json_paths` with:

```python
".lgwf/step_design_reason.json",
".lgwf/step_design_semantic_observation.json",
".lgwf/step_design_decision_analysis.json",
```

- [ ] **Step 5: Run the targeted tests and confirm they fail**

Run:

```powershell
python -m unittest `
  skills\lgwf-wf-tools\workflows\wf-create\tests\test_workflow_integrity.py `
  skills\lgwf-wf-tools\workflows\wf-create\tests\test_prompt_contracts.py `
  skills\lgwf-wf-tools\workflows\wf-create\tests\test_structured_contracts.py
```

Expected: FAIL because the new workflow, prompt, script, and schema files do not exist yet.

---

### Task 2: Add Script-Level Tests For OB Feedback And Decide

**Files:**
- Modify: `skills/lgwf-wf-tools/workflows/wf-create/tests/test_proposal_quality_gate.py`

- [ ] **Step 1: Add a test for structural gate source_refs and forbidden Markdown contracts**

Append this test method to `ProposalQualityGateTest`:

```python
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
            "03_confirm_step_designs/02_step_design_proposal/03_observe_step_designs/scripts/validate_step_designs_structure.py",
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads((lgwf_dir / "step_design_structural_gate.json").read_text(encoding="utf-8"))
        self.assertFalse(result["passed"])
        failures = {check["name"]: check["message"] for check in result["checks"] if not check["passed"]}
        self.assertIn("step_designs[0]_source_refs_present", failures)
```

- [ ] **Step 2: Add a test for OB merge preserving structural failures**

Append:

```python
def test_step_design_observation_merge_blocks_on_structural_failure(self) -> None:
    with tempfile.TemporaryDirectory() as temp:
        work_dir = Path(temp)
        lgwf_dir = work_dir / ".lgwf"
        write_json(
            lgwf_dir / "step_design_structural_gate.json",
            {
                "passed": False,
                "checks": [
                    {
                        "name": "step_designs[0]_source_refs_present",
                        "passed": False,
                        "message": "step_designs[0].source_refs 必须是非空数组",
                    }
                ],
            },
        )
        write_json(
            lgwf_dir / "step_design_semantic_observation.json",
            {
                "verdict": "pass",
                "semantic_passed": True,
                "blocking_issues": [],
                "valid_parts_to_preserve": ["step_designs[0]"],
                "reason_feedback": {
                    "repair_mode": "targeted_repair",
                    "priority_issue_ids": [],
                    "must_preserve": ["step_designs[0]"],
                    "must_change": [],
                    "forbidden_changes": ["不得写入 .lgwf/step_designs.json"],
                    "act_instruction_patch": [],
                },
            },
        )

        completed = run_script(
            work_dir,
            "03_confirm_step_designs/02_step_design_proposal/03_observe_step_designs/scripts/merge_step_design_observation.py",
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        observation = json.loads((lgwf_dir / "step_design_observation.json").read_text(encoding="utf-8"))
        self.assertFalse(observation["passed"])
        self.assertEqual(observation["verdict"], "revise")
        self.assertIn("step_designs[0]_source_refs_present", observation["issue_signatures"])
        self.assertIn("step_designs[0].source_refs 必须是非空数组", json.dumps(observation["reason_feedback"], ensure_ascii=False))
```

- [ ] **Step 3: Add a test for DECIDE route output**

Append:

```python
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
        write_json(
            lgwf_dir / "step_design_decision_analysis.json",
            {
                "recommended_next": "continue",
                "reason": "仍有 blocker，需要下一轮 targeted repair。",
                "no_progress_risk": False,
            },
        )

        completed = run_script(
            work_dir,
            "03_confirm_step_designs/02_step_design_proposal/04_decide_step_designs/scripts/decide_step_designs.py",
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        decision = json.loads((lgwf_dir / "step_designs_proposal_decision.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["next"], "continue")
        self.assertEqual(decision["next"], "continue")
        self.assertFalse(decision["passed"])
```

- [ ] **Step 4: Run the new tests and confirm they fail**

Run:

```powershell
python -m unittest skills\lgwf-wf-tools\workflows\wf-create\tests\test_proposal_quality_gate.py
```

Expected: FAIL because `03_observe_step_designs` and `04_decide_step_designs` scripts do not exist.

---

### Task 3: Rewrite The Step Design Proposal Workflow Topology

**Files:**
- Modify: `skills/lgwf-wf-tools/workflows/wf-create/wf/03_confirm_step_designs/02_step_design_proposal/workflow.lgwf`
- Modify: `skills/lgwf-wf-tools/workflows/wf-create/wf/03_confirm_step_designs/workflow.lgwf`

- [ ] **Step 1: Replace the REACT slot declarations**

Use this structure in `02_step_design_proposal/workflow.lgwf`:

```lgwf
WORKFLOW step_design_proposal;
ENTRY prepare_step_design_proposal_react_feedback;

DEFAULTS {
  ref_root workflow ".";
  timeout_seconds 900;
}

PY prepare_step_design_proposal_react_feedback
  SCRIPT "scripts/prepare_react_feedback.py"
  TIMEOUT 30
  RESULT state.lgwf_wf_create.step_design_proposal_react_feedback_prepare_result
  CONTRACT {
    WRITE workspace file ".lgwf/step_design_observation.json";
    WRITE workspace file ".lgwf/step_designs_proposal_quality_gate.json";
    WRITE workspace file ".lgwf/step_designs_proposal_decision.json";
  };

REACT step_design_proposal_react MAX 3
  CONTRACT {
  }
  REASON WORKFLOW reason_step_designs
    WORKFLOW "01_reason_step_designs/workflow.lgwf"
    RESULT state.lgwf_wf_create.step_design_reason_workflow_result
    CONTRACT {
      READ workspace file ".lgwf/business_flow.json";
      READ workspace file ".lgwf/create_requirements.json";
      READ workspace file ".lgwf/scaffold_package_result.json";
      READ workspace file ".lgwf/step_design_observation.json";
      READ workspace file ".lgwf/step_designs_proposal_decision.json";
      WRITE workspace file ".lgwf/step_design_reason.json";
    }
  ACT WORKFLOW act_step_designs
    WORKFLOW "02_act_step_designs/workflow.lgwf"
    RESULT state.lgwf_wf_create.step_design_act_workflow_result
    CONTRACT {
      READ workspace file ".lgwf/business_flow.json";
      READ workspace file ".lgwf/create_requirements.json";
      READ workspace file ".lgwf/scaffold_package_result.json";
      READ workspace file ".lgwf/step_design_reason.json";
      READ workspace dir ".lgwf/create_reference_context";
      READ workspace file ".lgwf/create_reference_context/step-design-reference-index.md";
      WRITE workspace file ".lgwf/step_designs_proposal.json";
    }
  OBSERVE WORKFLOW observe_step_designs
    WORKFLOW "03_observe_step_designs/workflow.lgwf"
    RESULT state.lgwf_wf_create.step_design_observe_workflow_result
    CONTRACT {
      READ workspace file ".lgwf/business_flow.json";
      READ workspace file ".lgwf/create_requirements.json";
      READ workspace file ".lgwf/scaffold_package_result.json";
      READ workspace file ".lgwf/step_design_reason.json";
      READ workspace file ".lgwf/step_designs_proposal.json";
      WRITE workspace file ".lgwf/step_design_structural_gate.json";
      WRITE workspace file ".lgwf/step_design_semantic_observation.json";
      WRITE workspace file ".lgwf/step_design_observation.json";
      WRITE workspace file ".lgwf/step_designs_proposal_quality_gate.json";
    }
  DECIDE WORKFLOW decide_step_designs
    WORKFLOW "04_decide_step_designs/workflow.lgwf"
    RESULT state.lgwf_wf_create.step_design_decide_workflow_result
    CONTRACT {
      READ workspace file ".lgwf/step_design_observation.json";
      READ workspace file ".lgwf/step_designs_proposal.json";
      WRITE workspace file ".lgwf/step_design_decision_analysis.json";
      WRITE workspace file ".lgwf/step_designs_proposal_decision.json";
    };

PY assert_step_designs_proposal_quality_gate
  SCRIPT "scripts/assert_quality_gate.py"
  TIMEOUT 30
  RESULT state.lgwf_wf_create.step_designs_proposal_quality_gate_assert_result
  UPDATES_STATE
  CONTRACT {
    READ workspace file ".lgwf/step_design_observation.json";
    READ workspace file ".lgwf/step_designs_proposal_quality_gate.json";
    WRITE state.lgwf_wf_create.step_designs_proposal_quality_gate_asserted;
  };

FLOW prepare_step_design_proposal_react_feedback
  THEN step_design_proposal_react
  THEN assert_step_designs_proposal_quality_gate;
```

- [ ] **Step 2: Extend the parent contract**

In `03_confirm_step_designs/workflow.lgwf`, add these writes under `STEP step_design_proposal CONTRACT`:

```lgwf
WRITE workspace file ".lgwf/step_design_reason.json";
WRITE workspace file ".lgwf/step_design_structural_gate.json";
WRITE workspace file ".lgwf/step_design_semantic_observation.json";
WRITE workspace file ".lgwf/step_design_observation.json";
WRITE workspace file ".lgwf/step_design_decision_analysis.json";
```

- [ ] **Step 3: Run DSL resource existence test**

Run:

```powershell
python -m unittest skills\lgwf-wf-tools\workflows\wf-create\tests\test_workflow_integrity.py::WorkflowCreateIntegrityTest.test_all_workflow_resource_references_exist
```

Expected: FAIL until slot workflow files are added.

---

### Task 4: Implement REASON Slot Workflow And Prompt

**Files:**
- Create: `.../02_step_design_proposal/01_reason_step_designs/workflow.lgwf`
- Create: `.../02_step_design_proposal/01_reason_step_designs/agents/reason_step_designs.md`
- Create: `.../02_step_design_proposal/01_reason_step_designs/README.md`

- [ ] **Step 1: Add `workflow.lgwf`**

```lgwf
WORKFLOW reason_step_designs;
ENTRY reason_step_designs;

DEFAULTS {
  ref_root workflow ".";
  timeout_seconds 900;
}

CODEX reason_step_designs
  PROMPT "agents/reason_step_designs.md"
  CONTEXT workspace file ".lgwf/business_flow.json"
  CONTEXT workspace file ".lgwf/create_requirements.json"
  CONTEXT workspace file ".lgwf/scaffold_package_result.json"
  CONTEXT workspace file ".lgwf/step_design_observation.json"
  CONTEXT workspace file ".lgwf/step_designs_proposal_decision.json"
  CONTEXT workspace file ".lgwf/step_designs_proposal.json"
  OUTPUT_JSON ".lgwf/step_design_reason.json" AS_FILE
  TIMEOUT 900
  RESULT state.lgwf_wf_create.step_design_reason_result
  CONTRACT {
    READ workspace file ".lgwf/business_flow.json";
    READ workspace file ".lgwf/create_requirements.json";
    READ workspace file ".lgwf/scaffold_package_result.json";
    READ workspace file ".lgwf/step_design_observation.json";
    READ workspace file ".lgwf/step_designs_proposal_decision.json";
    READ workspace file ".lgwf/step_designs_proposal.json";
    WRITE workspace file ".lgwf/step_design_reason.json";
  };

FLOW reason_step_designs;
```

- [ ] **Step 2: Add the REASON prompt**

`reason_step_designs.md` must include these sections exactly: `Role`, `Inputs`, `Task`, `Output Format`, `Constraints`.

Output schema:

```json
{
  "round_mode": "first_round",
  "repair_focus": [],
  "must_preserve": [],
  "must_change": [],
  "forbidden_changes": [
    "不得写入 .lgwf/step_designs.json",
    "不得重新设计已确认 create_requirements.json",
    "不得重新设计已确认 business_flow.json",
    "不得新增 scaffold_plan 之外的根目录结构"
  ],
  "act_instructions": [],
  "risk_notes": []
}
```

Prompt constraints:
- 首轮使用 `round_mode=first_round`。
- 若 `.lgwf/step_design_observation.json.reason_feedback` 存在，必须逐项吸收为 `repair_focus`、`must_change` 和 `act_instructions`。
- 不生成 `.lgwf/step_designs_proposal.json`。
- 不读取 `wf/04_implement_steps_react/`、`tests/`、目标 package 目录或仓库其他源码。

- [ ] **Step 3: Add the README**

README must document:
- 职责：只把 OB 反馈编译成本轮 ACT 指令。
- 输入：requirements、business_flow、scaffold、observation、previous decision、previous proposal。
- 输出：`.lgwf/step_design_reason.json`。
- 禁止事项：不生成 proposal，不写 confirmed artifact，不扩大范围。

---

### Task 5: Implement ACT Slot Workflow And Prompt

**Files:**
- Create: `.../02_step_design_proposal/02_act_step_designs/workflow.lgwf`
- Create: `.../02_step_design_proposal/02_act_step_designs/agents/act_step_designs.md`
- Create: `.../02_step_design_proposal/02_act_step_designs/README.md`

- [ ] **Step 1: Add `workflow.lgwf`**

```lgwf
WORKFLOW act_step_designs;
ENTRY act_step_designs;

DEFAULTS {
  ref_root workflow ".";
  timeout_seconds 900;
}

CODEX act_step_designs
  PROMPT "agents/act_step_designs.md"
  CONTEXT workspace file ".lgwf/step_design_reason.json"
  CONTEXT workspace file ".lgwf/business_flow.json"
  CONTEXT workspace file ".lgwf/create_requirements.json"
  CONTEXT workspace file ".lgwf/scaffold_package_result.json"
  CONTEXT workspace dir ".lgwf/create_reference_context"
  CONTEXT workspace file ".lgwf/create_reference_context/step-design-reference-index.md"
  OUTPUT_JSON ".lgwf/step_designs_proposal.json" AS_FILE
  TIMEOUT 900
  RESULT state.lgwf_wf_create.step_design_act_result
  CONTRACT {
    READ workspace file ".lgwf/step_design_reason.json";
    READ workspace file ".lgwf/business_flow.json";
    READ workspace file ".lgwf/create_requirements.json";
    READ workspace file ".lgwf/scaffold_package_result.json";
    READ workspace dir ".lgwf/create_reference_context";
    READ workspace file ".lgwf/create_reference_context/step-design-reference-index.md";
    WRITE workspace file ".lgwf/step_designs_proposal.json";
  };

FLOW act_step_designs;
```

- [ ] **Step 2: Add the ACT prompt**

`act_step_designs.md` output must keep the existing proposal contract:

```json
{
  "workflow_id": "",
  "workflow_name": "",
  "target_package_root": "",
  "package_profile": "",
  "source_business_flow_stages": [],
  "step_designs": [
    {
      "step_slug": "",
      "step_name": "",
      "stage_id": "",
      "goal": "",
      "inputs": [],
      "outputs": [],
      "dependencies": [],
      "implementation_suggestions": [],
      "acceptance_notes": [],
      "out_of_scope": [],
      "confirmation_points": [],
      "target_files": [],
      "target_dirs": [],
      "runtime_artifacts": [],
      "source_refs": [],
      "risk_notes": []
    }
  ],
  "design_rationale": []
}
```

Prompt constraints:
- 必须落实 `.lgwf/step_design_reason.json.act_instructions`。
- `round_mode=targeted_repair` 时只改 `must_change` 相关字段，保留 `must_preserve`。
- `source_refs` 必须是非空数组，指向 requirements、business_flow、scaffold_plan 或 reference index 的具体来源。
- 不写 `.lgwf/step_designs.json`。
- 不生成 `docs/steps/*.md` 或 `wf/docs/steps/*.md`。

---

### Task 6: Implement OBSERVE Slot Workflow, Structural Gate, Semantic Prompt, And Merge

**Files:**
- Create: `.../02_step_design_proposal/03_observe_step_designs/workflow.lgwf`
- Create: `.../02_step_design_proposal/03_observe_step_designs/agents/observe_step_designs.md`
- Create: `.../02_step_design_proposal/03_observe_step_designs/scripts/validate_step_designs_structure.py`
- Create: `.../02_step_design_proposal/03_observe_step_designs/scripts/merge_step_design_observation.py`
- Create: `.../02_step_design_proposal/03_observe_step_designs/README.md`

- [ ] **Step 1: Add `workflow.lgwf`**

```lgwf
WORKFLOW observe_step_designs;
ENTRY validate_step_designs_structure;

DEFAULTS {
  ref_root workflow ".";
  timeout_seconds 900;
}

PY validate_step_designs_structure
  SCRIPT "scripts/validate_step_designs_structure.py"
  TIMEOUT 30
  RESULT state.lgwf_wf_create.step_design_structural_gate
  UPDATES_STATE
  CONTRACT {
    READ workspace file ".lgwf/business_flow.json";
    READ workspace file ".lgwf/create_requirements.json";
    READ workspace file ".lgwf/scaffold_package_result.json";
    READ workspace file ".lgwf/step_designs_proposal.json";
    WRITE workspace file ".lgwf/step_design_structural_gate.json";
  };

CODEX observe_step_designs
  PROMPT "agents/observe_step_designs.md"
  CONTEXT workspace file ".lgwf/step_design_reason.json"
  CONTEXT workspace file ".lgwf/step_designs_proposal.json"
  CONTEXT workspace file ".lgwf/step_design_structural_gate.json"
  CONTEXT workspace file ".lgwf/business_flow.json"
  CONTEXT workspace file ".lgwf/create_requirements.json"
  CONTEXT workspace file ".lgwf/scaffold_package_result.json"
  OUTPUT_JSON ".lgwf/step_design_semantic_observation.json" AS_FILE
  TIMEOUT 900
  RESULT state.lgwf_wf_create.step_design_semantic_observation_result
  CONTRACT {
    READ workspace file ".lgwf/step_design_reason.json";
    READ workspace file ".lgwf/step_designs_proposal.json";
    READ workspace file ".lgwf/step_design_structural_gate.json";
    READ workspace file ".lgwf/business_flow.json";
    READ workspace file ".lgwf/create_requirements.json";
    READ workspace file ".lgwf/scaffold_package_result.json";
    WRITE workspace file ".lgwf/step_design_semantic_observation.json";
  };

PY merge_step_design_observation
  SCRIPT "scripts/merge_step_design_observation.py"
  TIMEOUT 30
  RESULT state.lgwf_wf_create.step_design_observation
  UPDATES_STATE
  CONTRACT {
    READ workspace file ".lgwf/step_design_structural_gate.json";
    READ workspace file ".lgwf/step_design_semantic_observation.json";
    WRITE workspace file ".lgwf/step_design_observation.json";
    WRITE workspace file ".lgwf/step_designs_proposal_quality_gate.json";
  };

FLOW validate_step_designs_structure
  THEN observe_step_designs
  THEN merge_step_design_observation;
```

- [ ] **Step 2: Implement structural gate script**

Port the existing `validate_step_designs_proposal.py` logic, then add checks for:
- `source_refs` is a non-empty array for every step.
- `target_files`, `target_dirs`, and `runtime_artifacts`, when present, are arrays.
- no target file path starts with `.lgwf/`, contains `..`, contains a drive letter, or is absolute.
- every failed check has stable `name` and actionable `message`.

The script writes `.lgwf/step_design_structural_gate.json` and prints:

```json
{
  "lgwf_wf_create.step_design_structural_gate": {}
}
```

- [ ] **Step 3: Add semantic OBSERVE prompt**

`observe_step_designs.md` must output:

```json
{
  "verdict": "pass",
  "semantic_passed": true,
  "blocking_issues": [],
  "valid_parts_to_preserve": [],
  "reason_feedback": {
    "repair_mode": "targeted_repair",
    "priority_issue_ids": [],
    "must_preserve": [],
    "must_change": [],
    "forbidden_changes": [
      "不得写入 .lgwf/step_designs.json",
      "不得重新设计已确认 business_flow",
      "不得新增 scaffold_plan 之外的根目录结构"
    ],
    "act_instruction_patch": []
  }
}
```

Semantic audit criteria:
- proposal 是否覆盖 business flow 和 scaffold stage manifest。
- 每个 step 是否足够让实现阶段直接消费。
- `acceptance_notes` 是否能转为 pass/fail。
- `out_of_scope` 是否明确排除 `lgwf-wf-prompt-fix`、`lgwf-wf-tools`、自动修复和端到端运行保证。
- 是否存在泛化描述、旧 Markdown 契约、实现阶段仍需猜测的字段。

- [ ] **Step 4: Implement merge script**

`merge_step_design_observation.py` combines structural and semantic results into:

```json
{
  "passed": false,
  "verdict": "revise",
  "structural_passed": false,
  "semantic_passed": true,
  "blocking_issues": [],
  "failed_checks": [],
  "issue_signatures": [],
  "valid_parts_to_preserve": [],
  "reason_feedback": {}
}
```

Rules:
- `passed=true` only when structural gate passed and semantic observation has `semantic_passed=true`.
- structural failures become synthetic `blocking_issues` with `issue_id` equal to the failed check `name`.
- `issue_signatures` includes every structural failed check name and every semantic `blocking_issues[].issue_id`.
- write identical combined payload to `.lgwf/step_designs_proposal_quality_gate.json` for compatibility with the final assert node.

---

### Task 7: Implement DECIDE Slot Workflow And Deterministic Route Writer

**Files:**
- Create: `.../02_step_design_proposal/04_decide_step_designs/workflow.lgwf`
- Create: `.../02_step_design_proposal/04_decide_step_designs/agents/decide_step_designs.md`
- Create: `.../02_step_design_proposal/04_decide_step_designs/scripts/decide_step_designs.py`
- Create: `.../02_step_design_proposal/04_decide_step_designs/README.md`

- [ ] **Step 1: Add `workflow.lgwf`**

```lgwf
WORKFLOW decide_step_designs;
ENTRY decide_step_designs;

DEFAULTS {
  ref_root workflow ".";
  timeout_seconds 900;
}

CODEX decide_step_designs
  PROMPT "agents/decide_step_designs.md"
  CONTEXT workspace file ".lgwf/step_design_observation.json"
  CONTEXT workspace file ".lgwf/step_designs_proposal.json"
  OUTPUT_JSON ".lgwf/step_design_decision_analysis.json" AS_FILE
  TIMEOUT 300
  RESULT state.lgwf_wf_create.step_design_decision_analysis_result
  CONTRACT {
    READ workspace file ".lgwf/step_design_observation.json";
    READ workspace file ".lgwf/step_designs_proposal.json";
    WRITE workspace file ".lgwf/step_design_decision_analysis.json";
  };

PY write_step_design_decision
  SCRIPT "scripts/decide_step_designs.py"
  TIMEOUT 30
  RESULT state.lgwf_wf_create.step_designs_proposal_decision_result
  UPDATES_STATE
  CONTRACT {
    READ workspace file ".lgwf/step_design_observation.json";
    READ workspace file ".lgwf/step_design_decision_analysis.json";
    WRITE workspace file ".lgwf/step_designs_proposal_decision.json";
  };

FLOW decide_step_designs
  THEN write_step_design_decision;
```

- [ ] **Step 2: Add decision prompt**

Prompt output:

```json
{
  "recommended_next": "continue",
  "reason": "",
  "repeat_issue_signatures": [],
  "no_progress_risk": false
}
```

Constraints:
- Codex only explains whether the current observation looks repairable.
- Codex does not write `next`.
- If `step_design_observation.passed=true`, recommend `exit`.
- If blocking issues remain, recommend `continue`.

- [ ] **Step 3: Implement `decide_step_designs.py`**

Script rules:
- read `.lgwf/step_design_observation.json`;
- read `.lgwf/step_design_decision_analysis.json` if present;
- write `.lgwf/step_designs_proposal_decision.json`;
- print JSON containing top-level `"next"` so `subgraph.react` can route.

Decision contract:

```json
{
  "next": "continue",
  "passed": false,
  "reason": "",
  "issue_signatures": [],
  "observation_file": ".lgwf/step_design_observation.json",
  "decision_analysis_file": ".lgwf/step_design_decision_analysis.json"
}
```

Route rule:
- `next="exit"` if observation `passed is True`.
- otherwise `next="continue"`.

---

### Task 8: Update Initialization And Final Assert Scripts

**Files:**
- Modify: `.../02_step_design_proposal/scripts/prepare_react_feedback.py`
- Modify: `.../02_step_design_proposal/scripts/assert_quality_gate.py`

- [ ] **Step 1: Initialize the new feedback files**

`prepare_react_feedback.py` writes:

```json
{
  "passed": false,
  "verdict": "not_started",
  "structural_passed": false,
  "semantic_passed": false,
  "blocking_issues": [],
  "failed_checks": [],
  "issue_signatures": [],
  "valid_parts_to_preserve": [],
  "reason_feedback": {
    "repair_mode": "first_round",
    "priority_issue_ids": [],
    "must_preserve": [],
    "must_change": [],
    "forbidden_changes": ["不得写入 .lgwf/step_designs.json"],
    "act_instruction_patch": []
  }
}
```

to `.lgwf/step_design_observation.json`, and keeps `{}` initialization for:
- `.lgwf/step_designs_proposal_quality_gate.json`
- `.lgwf/step_designs_proposal_decision.json`

- [ ] **Step 2: Assert combined observation**

`assert_quality_gate.py` should prefer `.lgwf/step_design_observation.json`; if missing, fall back to `.lgwf/step_designs_proposal_quality_gate.json`. It raises:

```text
step designs proposal quality gate failed after ReAct repair: <joined issue messages>
```

when `passed is not True`.

---

### Task 9: Update Prompt And Schema Registry Tests To Pass

**Files:**
- Modify: `.../resources/codex_output_schemas.json`
- Modify: `.../tests/test_prompt_contracts.py`

- [ ] **Step 1: Add schema registry entries**

Add entries under `codex_output_json_schemas`:

```json
".lgwf/step_design_reason.json": {
  "type": "object",
  "required": ["round_mode", "act_instructions", "forbidden_changes"]
},
".lgwf/step_design_semantic_observation.json": {
  "type": "object",
  "required": ["verdict", "semantic_passed", "blocking_issues", "reason_feedback"]
},
".lgwf/step_design_decision_analysis.json": {
  "type": "object",
  "required": ["recommended_next", "reason", "no_progress_risk"]
}
```

- [ ] **Step 2: Add prompt contract tests**

Add assertions in `test_step_design_prompt_stays_inside_design_node_contract` for each new prompt:

```python
reason_prompt = read("03_confirm_step_designs/02_step_design_proposal/01_reason_step_designs/agents/reason_step_designs.md")
act_prompt = read("03_confirm_step_designs/02_step_design_proposal/02_act_step_designs/agents/act_step_designs.md")
observe_prompt = read("03_confirm_step_designs/02_step_design_proposal/03_observe_step_designs/agents/observe_step_designs.md")
decide_prompt = read("03_confirm_step_designs/02_step_design_proposal/04_decide_step_designs/agents/decide_step_designs.md")

self.assertIn("reason_feedback", reason_prompt)
self.assertIn("act_instructions", act_prompt)
self.assertIn("blocking_issues", observe_prompt)
self.assertIn("recommended_next", decide_prompt)
self.assertNotIn("workflow control", decide_prompt.lower())
```

---

### Task 10: Update Documentation And Artifact Contracts

**Files:**
- Modify: `.../02_step_design_proposal/README.md`
- Modify: `.../03_confirm_step_designs/README.md`
- Modify: `.../wf/artifact_contracts.json`

- [ ] **Step 1: Document the depth exception**

In `02_step_design_proposal/README.md`, add:

```markdown
## Slot workflow 边界说明

本子流程在 `REACT step_design_proposal_react` 的四个 slot 下各使用一个局部 workflow。原因是每个 slot 都需要 Codex 语义分析，同时 `OBSERVE` 和 `DECIDE` 还必须包含确定性脚本来生成可审计的 feedback 与 `next` route。LGWF `REACT` 每个 slot 只能声明一个 task，因此这里以 slot workflow 封装“Codex 分析 + 确定性契约写入”，避免把 route 判断交给 Codex。
```

- [ ] **Step 2: Document OB feedback flow**

Add:

```markdown
`OBSERVE` 的正式反馈产物是 `.lgwf/step_design_observation.json`。下一轮 `REASON` 只能通过其中的 `reason_feedback` 制定修复策略，不能直接根据上一轮 Codex 输出自由重写步骤设计。
```

- [ ] **Step 3: Update artifact contracts**

Add runtime artifacts:

```json
".lgwf/step_design_reason.json",
".lgwf/step_design_structural_gate.json",
".lgwf/step_design_semantic_observation.json",
".lgwf/step_design_observation.json",
".lgwf/step_design_decision_analysis.json"
```

Keep `.lgwf/step_designs_proposal_quality_gate.json` and `.lgwf/step_designs_proposal_decision.json` for compatibility and final assertion.

---

### Task 11: Remove Old Single-Prompt Proposal Files

**Files:**
- Delete: `.../02_step_design_proposal/agents/design_steps_react.md`
- Delete: `.../02_step_design_proposal/scripts/prepare_react_context.py`
- Delete: `.../02_step_design_proposal/scripts/validate_step_designs_proposal.py`
- Delete: `.../02_step_design_proposal/scripts/decide_react.py`

- [ ] **Step 1: Remove old files after new tests pass locally**

Use `apply_patch` delete hunks for these files.

- [ ] **Step 2: Confirm no workflow references remain**

Run:

```powershell
rg -n "design_steps_react|prepare_react_context|validate_step_designs_proposal|decide_react" skills\lgwf-wf-tools\workflows\wf-create\wf\03_confirm_step_designs
```

Expected: no matches.

---

### Task 12: Full Verification

**Files:**
- No source changes.

- [ ] **Step 1: Run wf-create tests**

```powershell
python -m unittest discover skills\lgwf-wf-tools\workflows\wf-create\tests
```

Expected: PASS.

- [ ] **Step 2: Run lgwf-wf-tools tests**

```powershell
python -m unittest discover skills\lgwf-wf-tools\tests
```

Expected: PASS.

- [ ] **Step 3: Run package doctor**

```powershell
python skills\lgwf-wf-tools\scripts\doctor_lgwf_wf_tools.py
```

Expected: command exits 0.

- [ ] **Step 4: Check for resource path violations**

```powershell
rg -n "\.\.|[A-Za-z]:[\\/]|https?://|file://" skills\lgwf-wf-tools\workflows\wf-create\wf\03_confirm_step_designs\02_step_design_proposal
```

Expected: no matches in `workflow.lgwf` resource references; prompt examples may mention forbidden patterns only as negative constraints.

---

## Self-Review

Spec coverage:
- 每个 ReAct slot 引入 Codex 分析：Task 3-7 cover `REASON/ACT/OBSERVE/DECIDE WORKFLOW` with Codex inside each slot.
- OB 设计与反馈给 REASON：Task 6 defines `.lgwf/step_design_observation.json.reason_feedback`; Task 4 makes REASON consume it.
- `.lgwf/step_designs.json` 仍是唯一确认后契约：Task 5/6/8 prohibit writing it; review/apply flow remains unchanged.
- 质量 gate 可审计：Task 6 structural gate + semantic observation + merge; Task 8 final assert.
- 确定性 route：Task 7 keeps `next` writing in Python.

Placeholder scan:
- No `TBD`, `TODO`, or undefined future task placeholders.
- Every new artifact has a path and producer.

Type consistency:
- `step_design_observation.json` uses `passed`, `verdict`, `issue_signatures`, `reason_feedback`.
- `step_design_reason.json` uses `round_mode`, `act_instructions`, `must_preserve`, `must_change`, `forbidden_changes`.
- `step_designs_proposal_decision.json` keeps existing compatibility name and includes top-level `next`.
