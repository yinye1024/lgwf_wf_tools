# Implementation First Pass Repair React Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `04_implement_steps_react` 改成“01 初版 FOREACH 实现 + 02 ReAct 修复优化”的两阶段结构，避免首轮无反馈 `REASON CODEX`，并让修复阶段把 observe 反馈明确传回 reason。

**Architecture:** 顶层 `04_implement_steps_react/workflow.lgwf` 只做顺序编排：先调用 `01_implement_units` 生成初版，再调用 `02_repair_implementation_react` 做 audit、reason、repair、observe、decide 闭环。`01_implement_units` 不再读取 `implementation_reason.md` 或 `implementation_observe.json`；`02_repair_implementation_react` 拥有自己的 ReAct spec 和四个 slot workflow，每个 slot 的 Codex prompt 只处理修复闭环内的语义分析。

**Tech Stack:** LGWF DSL `workflow.lgwf`、Python 3 标准库、Codex prompt Markdown、`unittest`、现有 wf-create 结构校验脚本。

---

## File Structure

目标结构：

```text
skills/lgwf-wf-tools/workflows/wf-create/wf/04_implement_steps_react/
  workflow.lgwf                         # 顶层薄编排：01 初版 -> 02 修复
  01_implement_units/
    workflow.lgwf                       # 初版 units：prepare -> FOREACH -> merge
    scripts/prepare_implementation_units.py
    scripts/merge_implementation_results.py
    01_implement_one_unit/
      workflow.lgwf
      agents/act_unit.md
      resources/codex_output_schemas.json
      scripts/prepare_current_implementation_unit.py
      scripts/publish_current_implementation_unit_result.py
  02_repair_implementation_react/
    workflow.lgwf                       # 修复 ReAct：initial observe -> REACT
    agents/spec.md                      # 唯一修复 ReAct spec
    01_reason_repair/
      workflow.lgwf
      agents/reason_repair.md
    02_act_repair/
      workflow.lgwf
      agents/act_repair.md
      resources/codex_output_schemas.json
      scripts/prepare_repair_context.py
      scripts/publish_repair_result.py
    03_observe_repair/
      workflow.lgwf
      agents/observe_repair.md
      scripts/audit_current_implementation.py
    04_decide_repair/
      workflow.lgwf
      agents/decide_repair.md
      scripts/decide_repair_implementation.py
```

删除或迁移：

- 删除 `04_implement_steps_react/agents/spec.md`，迁移为 `02_repair_implementation_react/agents/spec.md`。
- 删除 `04_implement_steps_react/agents/reason.md`，迁移为 `02_repair_implementation_react/01_reason_repair/agents/reason_repair.md`。
- 删除 `04_implement_steps_react/scripts/initialize_implementation_observe.py`。
- 删除 `04_implement_steps_react/scripts/decide_implementation.py`，迁移为 `02_repair_implementation_react/04_decide_repair/scripts/decide_repair_implementation.py`。
- 删除旧目录 `04_implement_steps_react/02_observe_audit/`，其 audit 脚本和 observe prompt 迁移到 `02_repair_implementation_react/03_observe_repair/`。

关键运行产物：

```text
.lgwf/implementation_units.json
.lgwf/current_implementation_unit_context.json
.lgwf/current_implementation_unit_result.json
.lgwf/implementation_result.json
.lgwf/implementation_audit_result.json
.lgwf/implementation_observe.json
.lgwf/implementation_repair_reason.json
.lgwf/implementation_repair_context.json
.lgwf/implementation_repair_result.json
.lgwf/implementation_repair_decision_analysis.json
.lgwf/implementation_decision.json
```

---

### Task 1: Add Failing Contract Tests For The New Topology

**Files:**

- Modify: `skills/lgwf-wf-tools/workflows/wf-create/tests/test_prompt_contracts.py`
- Modify: `skills/lgwf-wf-tools/workflows/wf-create/tests/test_structured_contracts.py`
- Modify: `skills/lgwf-wf-tools/workflows/wf-create/tests/test_workflow_integrity.py`

- [ ] **Step 1: Update Codex node inventory test**

In `test_prompt_contracts.py`, change `expected_nodes` inside `test_all_codex_prompt_nodes_have_contract_boundary_coverage` to remove the old top-level reason node and old observe path, then add the repair slot Codex nodes:

```python
expected_nodes = {
    "01_confirm_requirements/02_requirements_proposal/workflow.lgwf:act",
    "02_confirm_business_flow/01_business_flow_proposal/workflow.lgwf:act",
    "03_confirm_step_designs/02_step_design_proposal/01_reason_step_designs/workflow.lgwf:reason_step_designs",
    "03_confirm_step_designs/02_step_design_proposal/02_act_step_designs/workflow.lgwf:act_step_designs",
    "03_confirm_step_designs/02_step_design_proposal/03_observe_step_designs/workflow.lgwf:observe_step_designs",
    "03_confirm_step_designs/02_step_design_proposal/04_decide_step_designs/workflow.lgwf:decide_step_designs",
    "04_implement_steps_react/01_implement_units/01_implement_one_unit/workflow.lgwf:implement_current_unit",
    "04_implement_steps_react/02_repair_implementation_react/01_reason_repair/workflow.lgwf:reason_repair",
    "04_implement_steps_react/02_repair_implementation_react/02_act_repair/workflow.lgwf:act_repair",
    "04_implement_steps_react/02_repair_implementation_react/03_observe_repair/workflow.lgwf:observe_repair",
    "04_implement_steps_react/02_repair_implementation_react/04_decide_repair/workflow.lgwf:decide_repair",
}
```

- [ ] **Step 2: Update implementation topology assertions**

In `test_prompt_contracts.py`, replace assertions in `test_implementation_step_uses_deterministic_path_context` so they expect:

```python
self.assertNotIn("REACT implement_steps_react", implement_workflow)
self.assertIn('WORKFLOW "01_implement_units/workflow.lgwf"', implement_workflow)
self.assertIn('WORKFLOW "02_repair_implementation_react/workflow.lgwf"', implement_workflow)
self.assertRegex(implement_workflow, r"implement_initial_units\s+THEN\s+repair_implementation")
self.assertFalse((ROOT / "04_implement_steps_react/agents/spec.md").exists())
self.assertFalse((ROOT / "04_implement_steps_react/agents/reason.md").exists())
```

Add assertions for the repair workflow:

```python
repair_workflow = read("04_implement_steps_react/02_repair_implementation_react/workflow.lgwf")
self.assertIn("REACT repair_implementation_react MAX 3", repair_workflow)
self.assertIn("REASON WORKFLOW reason_repair", repair_workflow)
self.assertIn("ACT WORKFLOW act_repair", repair_workflow)
self.assertIn("OBSERVE WORKFLOW observe_repair", repair_workflow)
self.assertIn("DECIDE WORKFLOW decide_repair", repair_workflow)
self.assertIn('SPEC "agents/spec.md"', repair_workflow)
self.assertIn('WORKFLOW "03_observe_repair/workflow.lgwf"', repair_workflow)
```

- [ ] **Step 3: Replace shared spec test**

Rename `test_implementation_react_shared_rules_live_in_spec` to `test_repair_react_shared_rules_live_in_repair_spec`. Read the spec from:

```python
spec = read("04_implement_steps_react/02_repair_implementation_react/agents/spec.md")
```

Update `duplicate_specs` so these paths must not exist:

```python
duplicate_specs = (
    "04_implement_steps_react/agents/spec.md",
    "04_implement_steps_react/agents/reason.md",
    "04_implement_steps_react/01_implement_units/agents/spec.md",
    "04_implement_steps_react/01_implement_units/agents/act.md",
    "04_implement_steps_react/01_implement_units/01_implement_one_unit/agents/spec.md",
    "04_implement_steps_react/02_observe_audit",
    "04_implement_steps_react/README.md",
    "04_implement_steps_react/01_implement_units/README.md",
    "04_implement_steps_react/01_implement_units/01_implement_one_unit/README.md",
    "04_implement_steps_react/02_repair_implementation_react/README.md",
)
```

Update prompt reads:

```python
role_prompts = {
    "reason_repair": read("04_implement_steps_react/02_repair_implementation_react/01_reason_repair/agents/reason_repair.md"),
}
local_prompts = {
    "act_unit": read("04_implement_steps_react/01_implement_units/01_implement_one_unit/agents/act_unit.md"),
    "act_repair": read("04_implement_steps_react/02_repair_implementation_react/02_act_repair/agents/act_repair.md"),
    "observe_repair": read("04_implement_steps_react/02_repair_implementation_react/03_observe_repair/agents/observe_repair.md"),
    "decide_repair": read("04_implement_steps_react/02_repair_implementation_react/04_decide_repair/agents/decide_repair.md"),
}
```

- [ ] **Step 4: Update structured contract topology test**

In `test_structured_contracts.py`, replace `test_implementation_is_react_child_workflow_with_deterministic_audit_observe` expectations:

```python
self.assertNotIn("REACT implement_steps_react MAX 3", implement_workflow)
self.assertIn("STEP implement_initial_units", implement_workflow)
self.assertIn("STEP repair_implementation", implement_workflow)
self.assertIn('WORKFLOW "01_implement_units/workflow.lgwf"', implement_workflow)
self.assertIn('WORKFLOW "02_repair_implementation_react/workflow.lgwf"', implement_workflow)
self.assertIn("FLOW implement_initial_units", implement_workflow)
self.assertIn("THEN repair_implementation", implement_workflow)
```

Then add repair workflow assertions:

```python
repair_workflow = (ROOT / "04_implement_steps_react/02_repair_implementation_react/workflow.lgwf").read_text(encoding="utf-8")
self.assertIn("REACT repair_implementation_react MAX 3", repair_workflow)
self.assertIn("REASON WORKFLOW reason_repair", repair_workflow)
self.assertIn("ACT WORKFLOW act_repair", repair_workflow)
self.assertIn("OBSERVE WORKFLOW observe_repair", repair_workflow)
self.assertIn("DECIDE WORKFLOW decide_repair", repair_workflow)
```

- [ ] **Step 5: Update integrity test for observe-before-summary**

In `test_workflow_integrity.py`, update `test_implementation_observe_audit_runs_before_summary_and_handoff`:

```python
repair_workflow = (ROOT / "04_implement_steps_react/02_repair_implementation_react/workflow.lgwf").read_text(encoding="utf-8")
observe_workflow = (
    ROOT / "04_implement_steps_react/02_repair_implementation_react/03_observe_repair/workflow.lgwf"
).read_text(encoding="utf-8")

self.assertIn('WORKFLOW "02_repair_implementation_react/workflow.lgwf"', implement_workflow)
self.assertIn("REACT repair_implementation_react MAX 3", repair_workflow)
self.assertIn("PY audit_current_implementation", observe_workflow)
self.assertIn('SCRIPT "scripts/audit_current_implementation.py"', observe_workflow)
self.assertIn('READ workspace file ".lgwf/step_designs.json";', observe_workflow)
self.assertIn('WRITE workspace file ".lgwf/implementation_audit_result.json";', observe_workflow)
```

- [ ] **Step 6: Run focused tests and confirm failure**

Run:

```powershell
python -m unittest skills\lgwf-wf-tools\workflows\wf-create\tests\test_prompt_contracts.py skills\lgwf-wf-tools\workflows\wf-create\tests\test_structured_contracts.py skills\lgwf-wf-tools\workflows\wf-create\tests\test_workflow_integrity.py
```

Expected: FAIL because `02_repair_implementation_react` does not exist yet and top-level workflow still contains `REACT implement_steps_react`.

---

### Task 2: Make `01_implement_units` A Pure Initial Implementation FOREACH

**Files:**

- Modify: `skills/lgwf-wf-tools/workflows/wf-create/wf/04_implement_steps_react/01_implement_units/workflow.lgwf`
- Modify: `skills/lgwf-wf-tools/workflows/wf-create/wf/04_implement_steps_react/01_implement_units/scripts/prepare_implementation_units.py`
- Modify: `skills/lgwf-wf-tools/workflows/wf-create/wf/04_implement_steps_react/01_implement_units/01_implement_one_unit/scripts/prepare_current_implementation_unit.py`
- Modify: `skills/lgwf-wf-tools/workflows/wf-create/tests/test_implementation_units.py`

- [ ] **Step 1: Write tests proving initial units do not need reason/observe**

In `test_implementation_units.py`, change `seed_context` so it no longer writes:

```python
(lgwf_dir / "implementation_reason.md").write_text(...)
write_json(lgwf_dir / "implementation_observe.json", ...)
```

Update `test_initial_prepare_generates_disjoint_units`:

```python
self.assertEqual(result["selection_mode"], "full")
for unit in units:
    self.assertNotIn("implementation_reason", unit)
    self.assertNotIn("observe", unit)
    self.assertNotIn("repair_focus", unit)
```

Delete or move these repair-selection tests from `ImplementationUnitScriptsTest` because repair selection will belong to `02_repair_implementation_react`:

```python
test_prepare_uses_observe_failures_to_select_affected_units
test_prepare_selects_root_workflow_without_package_contracts_for_root_workflow_failure
test_prepare_selects_support_unit_for_unallocated_scaffold_dir_failure
```

- [ ] **Step 2: Run implementation unit tests and confirm failure**

Run:

```powershell
python -m unittest skills\lgwf-wf-tools\workflows\wf-create\tests\test_implementation_units.py
```

Expected: FAIL because `prepare_implementation_units.py` still reads `.lgwf/implementation_reason.md` and `.lgwf/implementation_observe.json`.

- [ ] **Step 3: Remove reason/observe reads from initial workflow contract**

In `01_implement_units/workflow.lgwf`, remove from `PY prepare_implementation_units` contract:

```lgwf
READ workspace file ".lgwf/implementation_observe.json";
READ workspace file ".lgwf/implementation_reason.md";
```

Keep only:

```lgwf
READ workspace file ".lgwf/implementation_context.json";
READ workspace file ".lgwf/scaffold_package_result.json";
READ workspace file ".lgwf/step_designs.json";
```

- [ ] **Step 4: Simplify `prepare_implementation_units.py`**

Change `make_unit` signature to remove `implementation_reason`, `observe`, and `repair_focus`:

```python
def make_unit(
    *,
    unit_id: str,
    unit_type: str,
    package_relative_files: list[str],
    package_relative_dirs: list[str],
    implementation_context: dict[str, Any],
    step_designs: list[dict[str, Any]],
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
```

Remove these keys from the unit payload:

```python
"implementation_reason": implementation_reason,
"observe": observe,
"repair_focus": repair_focus,
```

Change `all_units` signature to remove the same arguments and update every `make_unit` call.

Change `build_implementation_units` to always select the full unit list:

```python
def build_implementation_units(root: Path) -> dict[str, Any]:
    lgwf_dir = root / ".lgwf"
    implementation_context = load_json(lgwf_dir / "implementation_context.json")
    step_designs_payload = load_json(lgwf_dir / "step_designs.json")
    scaffold_plan = load_scaffold_plan(root)
    units = all_units(
        implementation_context,
        step_designs_payload,
        scaffold_plan,
    )
    result = {
        "selection_mode": "full",
        "unit_count": len(units),
        "implementation_units": units,
        "all_unit_ids": [str(unit.get("unit_id", "")) for unit in units],
        "failure_count": 0,
        "failures": [],
    }
    write_json(lgwf_dir / "implementation_units.json", result)
    return result
```

Delete unused helpers:

```python
failure_texts
is_initial_observe
selected_unit_ids
path_failure_matches
```

- [ ] **Step 5: Remove initial-unit repair wording**

In `prepare_current_implementation_unit.py`, remove this instruction:

```python
"优先处理 current_implementation_unit.repair_focus 中的 observe 失败项。"
```

Keep the staging and schema boundary instructions.

- [ ] **Step 6: Run implementation unit tests**

Run:

```powershell
python -m unittest skills\lgwf-wf-tools\workflows\wf-create\tests\test_implementation_units.py
```

Expected: PASS.

---

### Task 3: Convert The Top-Level Implementation Workflow Into Thin Sequencing

**Files:**

- Modify: `skills/lgwf-wf-tools/workflows/wf-create/wf/04_implement_steps_react/workflow.lgwf`
- Delete: `skills/lgwf-wf-tools/workflows/wf-create/wf/04_implement_steps_react/scripts/initialize_implementation_observe.py`
- Delete after migration: `skills/lgwf-wf-tools/workflows/wf-create/wf/04_implement_steps_react/scripts/decide_implementation.py`

- [ ] **Step 1: Replace top-level workflow content**

Rewrite `04_implement_steps_react/workflow.lgwf` as:

```lgwf
WORKFLOW implement_steps_react;
ENTRY FLOW implement_initial_units;

DEFAULTS {
  ref_root workflow ".";
  timeout_seconds 900;
}

STEP implement_initial_units
  WORKFLOW "01_implement_units/workflow.lgwf"
  RESULT state.lgwf_wf_create.initial_implementation_result
  CONTRACT {
    READ workspace file ".lgwf/create_reference_context/implementation-reference-index.md";
    READ workspace dir ".lgwf/create_reference_context";
    READ workspace file ".lgwf/implementation_context.json";
    READ workspace file ".lgwf/scaffold_package_result.json";
    READ workspace file ".lgwf/step_designs.json";
    WRITE workspace file ".lgwf/implementation_units.json";
    WRITE workspace file ".lgwf/implementation_result.json";
  };

STEP repair_implementation
  WORKFLOW "02_repair_implementation_react/workflow.lgwf"
  RESULT state.lgwf_wf_create.repair_implementation_result
  CONTRACT {
    READ workspace file ".lgwf/create_reference_context/implementation-reference-index.md";
    READ workspace dir ".lgwf/create_reference_context";
    READ workspace file ".lgwf/implementation_context.json";
    READ workspace file ".lgwf/implementation_result.json";
    READ workspace file ".lgwf/scaffold_package_result.json";
    READ workspace file ".lgwf/step_designs.json";
    WRITE workspace file ".lgwf/implementation_audit_result.json";
    WRITE workspace file ".lgwf/implementation_observe.json";
    WRITE workspace file ".lgwf/implementation_repair_reason.json";
    WRITE workspace file ".lgwf/implementation_repair_context.json";
    WRITE workspace file ".lgwf/implementation_repair_result.json";
    WRITE workspace file ".lgwf/implementation_repair_decision_analysis.json";
    WRITE workspace file ".lgwf/implementation_decision.json";
    WRITE workspace file ".lgwf/implementation_result.json";
  };

FLOW implement_initial_units
  THEN repair_implementation;
```

- [ ] **Step 2: Delete obsolete initialization script**

Delete:

```text
skills/lgwf-wf-tools/workflows/wf-create/wf/04_implement_steps_react/scripts/initialize_implementation_observe.py
```

Keep `scripts/decide_implementation.py` temporarily until Task 4 migrates it.

- [ ] **Step 3: Run focused topology tests**

Run:

```powershell
python -m unittest skills\lgwf-wf-tools\workflows\wf-create\tests\test_prompt_contracts.py skills\lgwf-wf-tools\workflows\wf-create\tests\test_structured_contracts.py
```

Expected: still FAIL because `02_repair_implementation_react` is not implemented yet.

---

### Task 4: Build `02_repair_implementation_react` As Slot Workflows

**Files:**

- Create: `skills/lgwf-wf-tools/workflows/wf-create/wf/04_implement_steps_react/02_repair_implementation_react/workflow.lgwf`
- Create: `skills/lgwf-wf-tools/workflows/wf-create/wf/04_implement_steps_react/02_repair_implementation_react/agents/spec.md`
- Create: `skills/lgwf-wf-tools/workflows/wf-create/wf/04_implement_steps_react/02_repair_implementation_react/01_reason_repair/workflow.lgwf`
- Create: `skills/lgwf-wf-tools/workflows/wf-create/wf/04_implement_steps_react/02_repair_implementation_react/01_reason_repair/agents/reason_repair.md`
- Create: `skills/lgwf-wf-tools/workflows/wf-create/wf/04_implement_steps_react/02_repair_implementation_react/02_act_repair/workflow.lgwf`
- Create: `skills/lgwf-wf-tools/workflows/wf-create/wf/04_implement_steps_react/02_repair_implementation_react/02_act_repair/agents/act_repair.md`
- Create: `skills/lgwf-wf-tools/workflows/wf-create/wf/04_implement_steps_react/02_repair_implementation_react/02_act_repair/resources/codex_output_schemas.json`
- Create: `skills/lgwf-wf-tools/workflows/wf-create/wf/04_implement_steps_react/02_repair_implementation_react/02_act_repair/scripts/prepare_repair_context.py`
- Create: `skills/lgwf-wf-tools/workflows/wf-create/wf/04_implement_steps_react/02_repair_implementation_react/02_act_repair/scripts/publish_repair_result.py`
- Create: `skills/lgwf-wf-tools/workflows/wf-create/wf/04_implement_steps_react/02_repair_implementation_react/03_observe_repair/workflow.lgwf`
- Create: `skills/lgwf-wf-tools/workflows/wf-create/wf/04_implement_steps_react/02_repair_implementation_react/03_observe_repair/agents/observe_repair.md`
- Create: `skills/lgwf-wf-tools/workflows/wf-create/wf/04_implement_steps_react/02_repair_implementation_react/03_observe_repair/scripts/audit_current_implementation.py`
- Create: `skills/lgwf-wf-tools/workflows/wf-create/wf/04_implement_steps_react/02_repair_implementation_react/04_decide_repair/workflow.lgwf`
- Create: `skills/lgwf-wf-tools/workflows/wf-create/wf/04_implement_steps_react/02_repair_implementation_react/04_decide_repair/agents/decide_repair.md`
- Create: `skills/lgwf-wf-tools/workflows/wf-create/wf/04_implement_steps_react/02_repair_implementation_react/04_decide_repair/scripts/decide_repair_implementation.py`
- Delete: `skills/lgwf-wf-tools/workflows/wf-create/wf/04_implement_steps_react/02_observe_audit/`
- Delete: `skills/lgwf-wf-tools/workflows/wf-create/wf/04_implement_steps_react/agents/`
- Delete: `skills/lgwf-wf-tools/workflows/wf-create/wf/04_implement_steps_react/scripts/decide_implementation.py`

- [ ] **Step 1: Write repair parent workflow**

Create `02_repair_implementation_react/workflow.lgwf`:

```lgwf
WORKFLOW repair_implementation_react;
ENTRY prepare_initial_observe;

DEFAULTS {
  ref_root workflow ".";
  timeout_seconds 900;
}

STEP prepare_initial_observe
  WORKFLOW "03_observe_repair/workflow.lgwf"
  RESULT state.lgwf_wf_create.initial_repair_observe_result
  CONTRACT {
    READ workspace file ".lgwf/implementation_context.json";
    READ workspace file ".lgwf/implementation_result.json";
    READ workspace file ".lgwf/scaffold_package_result.json";
    READ workspace file ".lgwf/step_designs.json";
    WRITE workspace file ".lgwf/implementation_audit_result.json";
    WRITE workspace file ".lgwf/implementation_observe.json";
  };

REACT repair_implementation_react MAX 3
  SPEC "agents/spec.md"
  CONTRACT {
  }
  REASON WORKFLOW reason_repair
    WORKFLOW "01_reason_repair/workflow.lgwf"
    RESULT state.lgwf_wf_create.repair_reason_result
    CONTRACT {
      READ workspace file ".lgwf/create_reference_context/implementation-reference-index.md";
      READ workspace dir ".lgwf/create_reference_context";
      READ workspace file ".lgwf/implementation_audit_result.json";
      READ workspace file ".lgwf/implementation_context.json";
      READ workspace file ".lgwf/implementation_decision.json";
      READ workspace file ".lgwf/implementation_observe.json";
      READ workspace file ".lgwf/implementation_result.json";
      READ workspace file ".lgwf/scaffold_package_result.json";
      READ workspace file ".lgwf/step_designs.json";
      WRITE workspace file ".lgwf/implementation_repair_reason.json";
    }
  ACT WORKFLOW act_repair
    WORKFLOW "02_act_repair/workflow.lgwf"
    RESULT state.lgwf_wf_create.repair_act_result
    CONTRACT {
      READ workspace file ".lgwf/create_reference_context/implementation-reference-index.md";
      READ workspace dir ".lgwf/create_reference_context";
      READ workspace file ".lgwf/implementation_audit_result.json";
      READ workspace file ".lgwf/implementation_context.json";
      READ workspace file ".lgwf/implementation_observe.json";
      READ workspace file ".lgwf/implementation_repair_reason.json";
      READ workspace file ".lgwf/implementation_result.json";
      READ workspace file ".lgwf/scaffold_package_result.json";
      READ workspace file ".lgwf/step_designs.json";
      WRITE workspace file ".lgwf/implementation_repair_context.json";
      WRITE workspace file ".lgwf/implementation_repair_result.json";
      WRITE workspace file ".lgwf/implementation_result.json";
    }
  OBSERVE WORKFLOW observe_repair
    WORKFLOW "03_observe_repair/workflow.lgwf"
    RESULT state.lgwf_wf_create.repair_observe_result
    CONTRACT {
      READ workspace file ".lgwf/implementation_audit_result.json";
      READ workspace file ".lgwf/implementation_context.json";
      READ workspace file ".lgwf/implementation_result.json";
      READ workspace file ".lgwf/scaffold_package_result.json";
      READ workspace file ".lgwf/step_designs.json";
      WRITE workspace file ".lgwf/implementation_audit_result.json";
      WRITE workspace file ".lgwf/implementation_observe.json";
    }
  DECIDE WORKFLOW decide_repair
    WORKFLOW "04_decide_repair/workflow.lgwf"
    RESULT state.lgwf_wf_create.repair_decide_result
    CONTRACT {
      READ workspace file ".lgwf/implementation_audit_result.json";
      READ workspace file ".lgwf/implementation_decision.json";
      READ workspace file ".lgwf/implementation_observe.json";
      WRITE workspace file ".lgwf/implementation_repair_decision_analysis.json";
      WRITE workspace file ".lgwf/implementation_decision.json";
    };

FLOW prepare_initial_observe
  THEN repair_implementation_react;
```

- [ ] **Step 2: Write repair spec**

Create `02_repair_implementation_react/agents/spec.md` with these sections:

```markdown
# repair_implementation_react 规格

## 职责

`repair_implementation_react` 只负责优化和修复 `01_implement_units` 已生成的初版 workflow package。它不负责首版设计解释，不重新拆解 `.lgwf/step_designs.json`，也不扩展已确认范围。

## 稳定输入

- `.lgwf/step_designs.json` 是唯一设计契约。
- `.lgwf/implementation_result.json` 是初版实现或上一轮修复后的实现结果。
- `.lgwf/implementation_audit_result.json` 是确定性 audit 事实源。
- `.lgwf/implementation_observe.json` 是 observe slot 对 audit 事实的语义归纳。
- `.lgwf/implementation_repair_reason.json` 是 reason slot 写给 act slot 的唯一修复计划。
- `.lgwf/create_reference_context/implementation-reference-index.md` 是 DSL/audit/module 参考入口。

## ReAct 边界

- REASON 只能把 observe/audit 反馈转成最小 repair plan。
- ACT 只能修改 repair plan 指定的 package-relative files；不能重新生成全包。
- OBSERVE 必须保留脚本 audit 的失败证据，不得把失败改写为通过。
- DECIDE 可以分析是否继续，但最终 `next` 只能由 Python 脚本写入。
- 修复阶段不得写 `.lgwf/step_designs.json`、不得修改 scaffold plan、不得读取 `03_confirm_step_designs` 的 prompt 或 tests 反推设计。
```

- [ ] **Step 3: Write reason slot workflow and prompt**

Create `01_reason_repair/workflow.lgwf`:

```lgwf
WORKFLOW reason_repair;
ENTRY reason_repair;

DEFAULTS {
  ref_root workflow ".";
  timeout_seconds 900;
}

CODEX reason_repair
  PROMPT "agents/reason_repair.md"
  CONTEXT workspace file ".lgwf/create_reference_context/implementation-reference-index.md"
  CONTEXT workspace dir ".lgwf/create_reference_context"
  CONTEXT workspace file ".lgwf/implementation_audit_result.json"
  CONTEXT workspace file ".lgwf/implementation_context.json"
  CONTEXT workspace file ".lgwf/implementation_decision.json"
  CONTEXT workspace file ".lgwf/implementation_observe.json"
  CONTEXT workspace file ".lgwf/implementation_result.json"
  CONTEXT workspace file ".lgwf/scaffold_package_result.json"
  CONTEXT workspace file ".lgwf/step_designs.json"
  OUTPUT_JSON ".lgwf/implementation_repair_reason.json" AS_FILE
  TIMEOUT 600
  RESULT state.lgwf_wf_create.repair_reason_json_result
  CONTRACT {
    READ workspace file ".lgwf/create_reference_context/implementation-reference-index.md";
    READ workspace dir ".lgwf/create_reference_context";
    READ workspace file ".lgwf/implementation_audit_result.json";
    READ workspace file ".lgwf/implementation_context.json";
    READ workspace file ".lgwf/implementation_decision.json";
    READ workspace file ".lgwf/implementation_observe.json";
    READ workspace file ".lgwf/implementation_result.json";
    READ workspace file ".lgwf/scaffold_package_result.json";
    READ workspace file ".lgwf/step_designs.json";
    WRITE workspace file ".lgwf/implementation_repair_reason.json";
  };
```

共同准则只通过父级 `REACT repair_implementation_react` 的 `SPEC "agents/spec.md"` 进入 ReAct；slot 子 workflow 不跨目录读取 `spec.md`，避免出现 `..` resource ref。

Create `01_reason_repair/agents/reason_repair.md`:

```markdown
# reason_repair

## Role

你是修复优化 ReAct 的 REASON slot。你的职责是把 `.lgwf/implementation_observe.json` 和 `.lgwf/implementation_audit_result.json` 中的失败反馈转成最小、可执行、可审计的修复计划。

## Task

1. 优先读取 `.lgwf/implementation_audit_result.json`，再读取 `.lgwf/implementation_observe.json`。
2. 如果 `passed=true`，输出 `repair_required=false`，且 `repair_units=[]`。
3. 如果 `passed=false`，提取 root cause、受影响文件、必须遵守的 spec 规则和修复验收检查。
4. 不重新解释 `.lgwf/step_designs.json` 的业务范围；只把失败反馈映射回已确认设计和已生成文件。

## Output

按 `OUTPUT_JSON ".lgwf/implementation_repair_reason.json" AS_FILE` 输出 UTF-8 JSON object：

```json
{
  "repair_required": true,
  "repair_goal": "",
  "root_causes": [],
  "affected_files": [],
  "repair_units": [
    {
      "unit_id": "repair_workflow_lgwf",
      "target_files": ["wf/workflow.lgwf"],
      "reason": "",
      "success_checks": []
    }
  ],
  "do_not_change": [],
  "success_checks": []
}
```
```

- [ ] **Step 4: Write act repair workflow**

Create `02_act_repair/workflow.lgwf`:

```lgwf
WORKFLOW act_repair;
ENTRY prepare_repair_context;

DEFAULTS {
  ref_root workflow ".";
  timeout_seconds 900;
}

PY prepare_repair_context
  SCRIPT "scripts/prepare_repair_context.py"
  TIMEOUT 60
  RESULT state.lgwf_wf_create.prepare_repair_context_result
  UPDATES_STATE
  CONTRACT {
    READ workspace file ".lgwf/implementation_audit_result.json";
    READ workspace file ".lgwf/implementation_context.json";
    READ workspace file ".lgwf/implementation_observe.json";
    READ workspace file ".lgwf/implementation_repair_reason.json";
    READ workspace file ".lgwf/implementation_result.json";
    READ workspace file ".lgwf/scaffold_package_result.json";
    READ workspace file ".lgwf/step_designs.json";
    WRITE workspace file ".lgwf/implementation_repair_context.json";
  };

CODEX act_repair
  PROMPT "agents/act_repair.md"
  CONTEXT workspace file ".lgwf/implementation_repair_context.json"
  CONTEXT workspace file ".lgwf/create_reference_context/implementation-reference-index.md"
  CONTEXT workspace dir ".lgwf/create_reference_context"
  OUTPUT_JSON ".lgwf/implementation_repair_result.json" AS_FILE
  TIMEOUT 1200
  RESULT state.lgwf_wf_create.act_repair_result
  CONTRACT {
    READ workspace file ".lgwf/implementation_repair_context.json";
    READ workspace file ".lgwf/create_reference_context/implementation-reference-index.md";
    READ workspace dir ".lgwf/create_reference_context";
    WRITE workspace file ".lgwf/implementation_repair_result.json";
    WRITE workspace dir ".lgwf/implementation_repair_stage";
  };

PY publish_repair_result
  SCRIPT "scripts/publish_repair_result.py"
  TIMEOUT 60
  RESULT state.lgwf_wf_create.publish_repair_result
  UPDATES_STATE
  CONTRACT {
    READ workspace file ".lgwf/implementation_repair_context.json";
    READ workspace file ".lgwf/implementation_repair_result.json";
    READ workspace file ".lgwf/implementation_result.json";
    READ workspace dir ".lgwf/implementation_repair_stage";
    WRITE workspace file ".lgwf/implementation_result.json";
  };

FLOW prepare_repair_context
  THEN act_repair
  THEN publish_repair_result;
```

- [ ] **Step 5: Implement repair context script**

Create `02_act_repair/scripts/prepare_repair_context.py` with behavior:

```python
def build_repair_context(root: Path) -> dict[str, Any]:
    lgwf_dir = root / ".lgwf"
    implementation_context = load_json(lgwf_dir / "implementation_context.json")
    repair_reason = load_json(lgwf_dir / "implementation_repair_reason.json")
    target_package_abs = Path(str(implementation_context["target_package_abs"])).resolve()
    repair_units = repair_reason.get("repair_units", [])
    output_files = unique(
        normalize_package_path(path)
        for unit in repair_units
        if isinstance(unit, dict)
        for path in unit.get("target_files", [])
    )
    if repair_reason.get("repair_required") is False:
        output_files = []
    context = {
        "repair_required": bool(repair_reason.get("repair_required")),
        "repair_reason": repair_reason,
        "target_package_root": implementation_context.get("target_package_root", ""),
        "unit_output_dir": ".lgwf/implementation_repair_stage",
        "workspace_output_files": [f".lgwf/implementation_repair_stage/{path}" for path in output_files],
        "target_files": output_files,
        "instructions": [
            "只修复 target_files 中列出的 package-relative 文件。",
            "只能写 workspace_output_files；不要直接写 target_package_abs。",
            "如果 repair_required=false，输出 no_op=true，不写 staged files。",
        ],
    }
    write_json(lgwf_dir / "implementation_repair_context.json", context)
    return context
```

Include `normalize_package_path` validation that rejects empty path, absolute path, drive letter, `.lgwf`, and `..`.

- [ ] **Step 6: Implement repair publish script**

Create `02_act_repair/scripts/publish_repair_result.py` with behavior:

```python
def publish_repair_result(root: Path) -> dict[str, Any]:
    lgwf_dir = root / ".lgwf"
    context = load_json(lgwf_dir / "implementation_repair_context.json")
    repair_result = load_json(lgwf_dir / "implementation_repair_result.json")
    implementation_result = load_json(lgwf_dir / "implementation_result.json")
    if context.get("repair_required") is False or repair_result.get("no_op") is True:
        implementation_result.setdefault("repair_rounds", []).append(
            {"status": "noop", "reason": "audit already passed"}
        )
        write_json(lgwf_dir / "implementation_result.json", implementation_result)
        return {"status": "noop", "published_files": []}
    allowed = set(context.get("target_files", []))
    generated = normalize_generated_files(repair_result.get("generated_files", []))
    unexpected = [path for path in generated if path not in allowed]
    if unexpected:
        raise ValueError(f"repair generated files outside target_files: {unexpected}")
    target_package_abs = Path(str(load_json(lgwf_dir / "implementation_context.json")["target_package_abs"])).resolve()
    stage_root = root / ".lgwf" / "implementation_repair_stage"
    published = []
    for relative in generated:
        source = stage_root / relative
        destination = target_package_abs / relative
        if not source.is_file():
            raise FileNotFoundError(f"missing staged repair file: {source}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(source.read_text(encoding="utf-8-sig"), encoding="utf-8")
        published.append({"path": relative})
    implementation_result.setdefault("repair_rounds", []).append(
        {"status": "ok", "generated_files": published}
    )
    implementation_result["generated_files"] = merge_generated_files(
        implementation_result.get("generated_files", []),
        published,
    )
    write_json(lgwf_dir / "implementation_result.json", implementation_result)
    return {"status": "ok", "published_files": published}
```

- [ ] **Step 7: Write act repair prompt**

Create `02_act_repair/agents/act_repair.md`:

```markdown
# act_repair

## Role

你是修复优化 ReAct 的 ACT slot。你的职责是根据 `.lgwf/implementation_repair_context.json` 修复已生成目标 package 中的指定文件。

## Inputs

- `.lgwf/implementation_repair_context.json`：唯一修复上下文。
- `.lgwf/create_reference_context/implementation-reference-index.md` 和 `.lgwf/create_reference_context`：只用于 DSL、audit 和模块边界参考。

## Task

1. 如果 `repair_required=false`，输出 `no_op=true`，不要写 staged files。
2. 如果需要修复，只读取 `implementation_repair_context.json` 指定的 target files 和必要参考。
3. 只写 `workspace_output_files` 列出的 staging 文件。
4. 不递归读取 `.lgwf`，不修改 `.lgwf/step_designs.json`，不直接写最终目标 package。

## Output

按 `OUTPUT_JSON ".lgwf/implementation_repair_result.json" AS_FILE` 输出：

```json
{
  "status": "ok",
  "no_op": false,
  "generated_files": [{"path": "wf/workflow.lgwf"}],
  "repair_notes": [],
  "remaining_risks": []
}
```
```

- [ ] **Step 8: Move audit script and observe prompt into observe slot**

Move the content of old `02_observe_audit/scripts/audit_created_package.py` to:

```text
02_repair_implementation_react/03_observe_repair/scripts/audit_current_implementation.py
```

Rename the main function call target from `audit_created_package` to `audit_current_implementation`, but keep output files:

```python
write_json(lgwf_dir / "implementation_audit_result.json", result)
write_json(lgwf_dir / "implementation_observe.json", result)
```

Create `03_observe_repair/workflow.lgwf`:

```lgwf
WORKFLOW observe_repair;
ENTRY audit_current_implementation;

DEFAULTS {
  ref_root workflow ".";
  timeout_seconds 600;
}

CONTEXT_SET observe_repair_context {
  workspace file ".lgwf/implementation_context.json";
  workspace file ".lgwf/implementation_result.json";
  workspace file ".lgwf/implementation_audit_result.json";
  workspace file ".lgwf/implementation_observe.json";
  workspace file ".lgwf/scaffold_package_result.json";
  workspace file ".lgwf/step_designs.json";
}

PY audit_current_implementation
  SCRIPT "scripts/audit_current_implementation.py"
  TIMEOUT 180
  RESULT state.lgwf_wf_create.implementation_audit_result
  UPDATES_STATE
  CONTRACT {
    READ workspace file ".lgwf/implementation_context.json";
    READ workspace file ".lgwf/implementation_result.json";
    READ workspace file ".lgwf/scaffold_package_result.json";
    READ workspace file ".lgwf/step_designs.json";
    WRITE workspace file ".lgwf/implementation_audit_result.json";
    WRITE workspace file ".lgwf/implementation_observe.json";
  };

CODEX observe_repair
  PROMPT "agents/observe_repair.md"
  CONTEXT observe_repair_context
  OUTPUT_JSON ".lgwf/implementation_observe.json" AS_FILE
  TIMEOUT 600
  RESULT state.lgwf_wf_create.implementation_observe_result
  CONTRACT {
    READ workspace file ".lgwf/implementation_audit_result.json";
    READ workspace file ".lgwf/implementation_context.json";
    READ workspace file ".lgwf/implementation_result.json";
    READ workspace file ".lgwf/scaffold_package_result.json";
    READ workspace file ".lgwf/step_designs.json";
    WRITE workspace file ".lgwf/implementation_observe.json";
  };

FLOW audit_current_implementation
  THEN observe_repair;
```

Move old `agents/observe.md` content into `observe_repair.md` and update names from `observe_implementation` to `observe_repair`.

- [ ] **Step 9: Write decide slot**

Create `04_decide_repair/workflow.lgwf`:

```lgwf
WORKFLOW decide_repair;
ENTRY decide_repair;

DEFAULTS {
  ref_root workflow ".";
  timeout_seconds 900;
}

CODEX decide_repair
  PROMPT "agents/decide_repair.md"
  CONTEXT workspace file ".lgwf/implementation_audit_result.json"
  CONTEXT workspace file ".lgwf/implementation_observe.json"
  CONTEXT workspace file ".lgwf/implementation_decision.json"
  OUTPUT_JSON ".lgwf/implementation_repair_decision_analysis.json" AS_FILE
  TIMEOUT 300
  RESULT state.lgwf_wf_create.repair_decision_analysis_result
  CONTRACT {
    READ workspace file ".lgwf/implementation_audit_result.json";
    READ workspace file ".lgwf/implementation_observe.json";
    READ workspace file ".lgwf/implementation_decision.json";
    WRITE workspace file ".lgwf/implementation_repair_decision_analysis.json";
  };

PY write_repair_decision
  SCRIPT "scripts/decide_repair_implementation.py"
  TIMEOUT 30
  RESULT state.lgwf_wf_create.implementation_decision_result
  UPDATES_STATE
  CONTRACT {
    READ workspace file ".lgwf/implementation_audit_result.json";
    READ workspace file ".lgwf/implementation_observe.json";
    READ workspace file ".lgwf/implementation_repair_decision_analysis.json";
    WRITE workspace file ".lgwf/implementation_decision.json";
  };

FLOW decide_repair
  THEN write_repair_decision;
```

Create `decide_repair.md`:

```markdown
# decide_repair

## Role

你是修复优化 ReAct 的 DECIDE slot 分析 agent。你只解释当前 observe/audit 是否应继续，不直接写 `next`。

## Task

1. 如果 audit 或 observe 的 `passed=true`，推荐 `recommended_next=exit`。
2. 如果仍有 `failures`、`checks` 失败或 `needs_post_fix=true`，推荐 `recommended_next=continue`。
3. 如果连续失败原因重复，设置 `no_progress_risk=true` 并记录 `repeat_issue_signatures`。

## Output

```json
{
  "recommended_next": "continue",
  "reason": "",
  "repeat_issue_signatures": [],
  "no_progress_risk": false
}
```
```

Create `decide_repair_implementation.py` by adapting old `scripts/decide_implementation.py`:

```python
def decide(work_dir: Path) -> dict[str, Any]:
    lgwf_dir = work_dir / ".lgwf"
    audit = read_json(lgwf_dir / "implementation_audit_result.json")
    observe = read_json(lgwf_dir / "implementation_observe.json")
    analysis = read_json(lgwf_dir / "implementation_repair_decision_analysis.json")
    source = audit if audit else observe
    passed = source.get("passed") is True
    result = {
        "next": "exit" if passed else "continue",
        "passed": passed,
        "reason": analysis.get(
            "reason",
            "authoring audit passed" if passed else "authoring audit failed; continue implementation repair",
        ),
        "source": "implementation_audit_result.json" if audit else "implementation_observe.json",
        "status": source.get("status", "passed" if passed else "failed"),
        "needs_post_fix": bool(source.get("needs_post_fix")),
        "failures": source.get("failures", []),
        "decision_analysis": analysis,
    }
    write_json(lgwf_dir / "implementation_decision.json", result)
    return result
```

- [ ] **Step 10: Delete old repair resources**

Delete:

```text
04_implement_steps_react/02_observe_audit/
04_implement_steps_react/agents/
04_implement_steps_react/scripts/decide_implementation.py
```

- [ ] **Step 11: Run focused topology tests**

Run:

```powershell
python -m unittest skills\lgwf-wf-tools\workflows\wf-create\tests\test_prompt_contracts.py skills\lgwf-wf-tools\workflows\wf-create\tests\test_structured_contracts.py
```

Expected: remaining FAILs only for schema registry, validator allow-list, and repair script unit tests not yet added.

---

### Task 5: Add Repair Script Unit Tests

**Files:**

- Modify: `skills/lgwf-wf-tools/workflows/wf-create/tests/test_implementation_units.py`

- [ ] **Step 1: Load repair modules in `setUpClass`**

Add:

```python
cls.prepare_repair = load_module(
    "02_repair_implementation_react/02_act_repair/scripts/prepare_repair_context.py",
    "prepare_repair_context",
)
cls.publish_repair = load_module(
    "02_repair_implementation_react/02_act_repair/scripts/publish_repair_result.py",
    "publish_repair_result",
)
cls.decide_repair = load_module(
    "02_repair_implementation_react/04_decide_repair/scripts/decide_repair_implementation.py",
    "decide_repair_implementation",
)
```

- [ ] **Step 2: Add repair context selection test**

Add:

```python
def test_prepare_repair_context_uses_reason_target_files(self) -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        self.seed_context(root)
        write_json(
            root / ".lgwf" / "implementation_repair_reason.json",
            {
                "repair_required": True,
                "repair_units": [
                    {
                        "unit_id": "repair_root",
                        "target_files": ["wf/workflow.lgwf"],
                        "reason": "root DSL failed",
                    }
                ],
            },
        )
        result = self.prepare_repair.build_repair_context(root)

        self.assertTrue(result["repair_required"])
        self.assertEqual(result["target_files"], ["wf/workflow.lgwf"])
        self.assertEqual(
            result["workspace_output_files"],
            [".lgwf/implementation_repair_stage/wf/workflow.lgwf"],
        )
        self.assertTrue((root / ".lgwf" / "implementation_repair_context.json").is_file())
```

- [ ] **Step 3: Add no-op repair context test**

Add:

```python
def test_prepare_repair_context_noops_when_audit_passed(self) -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        self.seed_context(root)
        write_json(
            root / ".lgwf" / "implementation_repair_reason.json",
            {"repair_required": False, "repair_units": []},
        )

        result = self.prepare_repair.build_repair_context(root)

        self.assertFalse(result["repair_required"])
        self.assertEqual(result["target_files"], [])
        self.assertEqual(result["workspace_output_files"], [])
```

- [ ] **Step 4: Add publish repair test**

Add:

```python
def test_publish_repair_result_updates_target_and_implementation_result(self) -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        target_package = self.seed_context(root)
        write_json(
            root / ".lgwf" / "implementation_result.json",
            {"status": "failed", "generated_files": [{"path": "wf/workflow.lgwf"}]},
        )
        write_json(
            root / ".lgwf" / "implementation_repair_context.json",
            {
                "repair_required": True,
                "target_files": ["wf/workflow.lgwf"],
                "unit_output_dir": ".lgwf/implementation_repair_stage",
            },
        )
        staged = root / ".lgwf" / "implementation_repair_stage" / "wf" / "workflow.lgwf"
        staged.parent.mkdir(parents=True, exist_ok=True)
        staged.write_text("WORKFLOW demo_workflow;\n", encoding="utf-8")
        write_json(
            root / ".lgwf" / "implementation_repair_result.json",
            {"status": "ok", "generated_files": [{"path": "wf/workflow.lgwf"}]},
        )

        result = self.publish_repair.publish_repair_result(root)

        self.assertEqual(result["status"], "ok")
        self.assertEqual((target_package / "wf" / "workflow.lgwf").read_text(encoding="utf-8"), "WORKFLOW demo_workflow;\n")
        updated = json.loads((root / ".lgwf" / "implementation_result.json").read_text(encoding="utf-8"))
        self.assertEqual(updated["repair_rounds"][0]["status"], "ok")
```

- [ ] **Step 5: Add publish path guard test**

Add:

```python
def test_publish_repair_result_rejects_files_outside_repair_context(self) -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        self.seed_context(root)
        write_json(
            root / ".lgwf" / "implementation_repair_context.json",
            {"repair_required": True, "target_files": ["wf/workflow.lgwf"]},
        )
        write_json(
            root / ".lgwf" / "implementation_repair_result.json",
            {"status": "ok", "generated_files": [{"path": "README.md"}]},
        )

        with self.assertRaises(ValueError):
            self.publish_repair.publish_repair_result(root)
```

- [ ] **Step 6: Run repair script tests and confirm failure**

Run:

```powershell
python -m unittest skills\lgwf-wf-tools\workflows\wf-create\tests\test_implementation_units.py
```

Expected: FAIL until Task 4 scripts are fully implemented.

- [ ] **Step 7: Implement scripts until tests pass**

Complete `prepare_repair_context.py`, `publish_repair_result.py`, and `decide_repair_implementation.py` according to Task 4 snippets.

- [ ] **Step 8: Run implementation unit tests**

Run:

```powershell
python -m unittest skills\lgwf-wf-tools\workflows\wf-create\tests\test_implementation_units.py
```

Expected: PASS.

---

### Task 6: Update Schema Registry And Artifact Contracts

**Files:**

- Modify: `skills/lgwf-wf-tools/workflows/wf-create/wf/04_implement_steps_react/01_implement_units/01_implement_one_unit/resources/codex_output_schemas.json`
- Create: `skills/lgwf-wf-tools/workflows/wf-create/wf/04_implement_steps_react/02_repair_implementation_react/02_act_repair/resources/codex_output_schemas.json`
- Modify: `skills/lgwf-wf-tools/workflows/wf-create/tests/test_prompt_contracts.py`
- Modify: `skills/lgwf-wf-tools/workflows/wf-create/wf/artifact_contracts.json`

- [ ] **Step 1: Update schema aggregation test**

In `test_codex_output_json_files_have_schema_registry_entries`, aggregate schema files instead of reading only the initial unit schema:

```python
schema_paths = (
    ROOT / "04_implement_steps_react/01_implement_units/01_implement_one_unit/resources/codex_output_schemas.json",
    ROOT / "04_implement_steps_react/02_repair_implementation_react/02_act_repair/resources/codex_output_schemas.json",
)
codex_schemas = {}
target_schemas = {}
for schema_path in schema_paths:
    schemas = json.loads(schema_path.read_text(encoding="utf-8"))
    codex_schemas.update(schemas.get("codex_output_json_schemas", {}))
    target_schemas.update(schemas.get("target_package_output_file_schemas", {}))
```

Update expected `output_json_paths` to include:

```python
".lgwf/implementation_repair_reason.json",
".lgwf/implementation_repair_result.json",
".lgwf/implementation_repair_decision_analysis.json",
```

- [ ] **Step 2: Add repair schema file**

Create `02_act_repair/resources/codex_output_schemas.json`:

```json
{
  "codex_output_json_schemas": {
    ".lgwf/implementation_repair_reason.json": {
      "type": "object",
      "required": ["repair_required", "repair_goal", "root_causes", "affected_files", "repair_units", "do_not_change", "success_checks"],
      "properties": {
        "repair_required": {"type": "boolean"},
        "repair_goal": {"type": "string"},
        "root_causes": {"type": "array"},
        "affected_files": {"type": "array"},
        "repair_units": {"type": "array"},
        "do_not_change": {"type": "array"},
        "success_checks": {"type": "array"}
      }
    },
    ".lgwf/implementation_repair_result.json": {
      "type": "object",
      "required": ["status", "no_op", "generated_files", "repair_notes", "remaining_risks"],
      "properties": {
        "status": {"type": "string"},
        "no_op": {"type": "boolean"},
        "generated_files": {"type": "array"},
        "repair_notes": {"type": "array"},
        "remaining_risks": {"type": "array"}
      }
    },
    ".lgwf/implementation_repair_decision_analysis.json": {
      "type": "object",
      "required": ["recommended_next", "reason", "repeat_issue_signatures", "no_progress_risk"],
      "properties": {
        "recommended_next": {"type": "string"},
        "reason": {"type": "string"},
        "repeat_issue_signatures": {"type": "array"},
        "no_progress_risk": {"type": "boolean"}
      }
    }
  },
  "target_package_output_file_schemas": {}
}
```

- [ ] **Step 3: Update artifact contracts**

In `wf/artifact_contracts.json`:

Remove:

```json
".lgwf/implementation_reason.md"
```

Add:

```json
".lgwf/implementation_repair_reason.json",
".lgwf/implementation_repair_context.json",
".lgwf/implementation_repair_result.json",
".lgwf/implementation_repair_decision_analysis.json"
```

Keep:

```json
".lgwf/implementation_audit_result.json",
".lgwf/implementation_observe.json",
".lgwf/implementation_decision.json",
".lgwf/implementation_result.json"
```

- [ ] **Step 4: Run schema contract test**

Run:

```powershell
python -m unittest skills\lgwf-wf-tools\workflows\wf-create\tests\test_prompt_contracts.py
```

Expected: PASS or only validator allow-list failures remain.

---

### Task 7: Update Workflow Structure Validator Allow-Lists

**Files:**

- Modify: `skills/lgwf-wf-tools/workflows/wf-create/scripts/validate_two_layer_workflow.py`
- Modify: `skills/lgwf-wf-tools/workflows/wf-create/tests/test_structured_contracts.py`

- [ ] **Step 1: Add repair slot workflows to allowed deep workflows**

Update `ALLOWED_DEEP_WORKFLOWS`:

```python
ALLOWED_DEEP_WORKFLOWS = {
    "03_confirm_step_designs/02_step_design_proposal/01_reason_step_designs/workflow.lgwf",
    "03_confirm_step_designs/02_step_design_proposal/02_act_step_designs/workflow.lgwf",
    "03_confirm_step_designs/02_step_design_proposal/03_observe_step_designs/workflow.lgwf",
    "03_confirm_step_designs/02_step_design_proposal/04_decide_step_designs/workflow.lgwf",
    "04_implement_steps_react/01_implement_units/01_implement_one_unit/workflow.lgwf",
    "04_implement_steps_react/02_repair_implementation_react/01_reason_repair/workflow.lgwf",
    "04_implement_steps_react/02_repair_implementation_react/02_act_repair/workflow.lgwf",
    "04_implement_steps_react/02_repair_implementation_react/03_observe_repair/workflow.lgwf",
    "04_implement_steps_react/02_repair_implementation_react/04_decide_repair/workflow.lgwf",
}
```

Update `ALLOWED_DEEP_WORKFLOW_PARENTS`:

```python
"04_implement_steps_react/02_repair_implementation_react/workflow.lgwf": {
    "01_reason_repair/workflow.lgwf",
    "02_act_repair/workflow.lgwf",
    "03_observe_repair/workflow.lgwf",
    "04_decide_repair/workflow.lgwf",
}
```

Update `README_OPTIONAL_WORKFLOWS`:

```python
"04_implement_steps_react/02_repair_implementation_react/workflow.lgwf",
"04_implement_steps_react/02_repair_implementation_react/01_reason_repair/workflow.lgwf",
"04_implement_steps_react/02_repair_implementation_react/02_act_repair/workflow.lgwf",
"04_implement_steps_react/02_repair_implementation_react/03_observe_repair/workflow.lgwf",
"04_implement_steps_react/02_repair_implementation_react/04_decide_repair/workflow.lgwf",
```

- [ ] **Step 2: Run structure validator test**

Run:

```powershell
python -m unittest skills\lgwf-wf-tools\workflows\wf-create\tests\test_structured_contracts.py
```

Expected: PASS or failures pointing to stale test assertions only.

---

### Task 8: Remove Old Prompt References And Update Prompt Quality Assertions

**Files:**

- Modify: `skills/lgwf-wf-tools/workflows/wf-create/tests/test_prompt_contracts.py`
- Modify: `skills/lgwf-wf-tools/workflows/wf-create/tests/test_structured_contracts.py`
- Modify: `skills/lgwf-wf-tools/workflows/wf-create/wf/04_implement_steps_react/01_implement_units/01_implement_one_unit/agents/act_unit.md`

- [ ] **Step 1: Remove stale `implementation_reason.md` assertions**

Search:

```powershell
rg -n "implementation_reason|agents/reason.md|02_observe_audit|OBSERVE WORKFLOW observe_audit|REASON CODEX" skills\lgwf-wf-tools\workflows\wf-create\tests skills\lgwf-wf-tools\workflows\wf-create\wf
```

Replace old expectations:

```text
implementation_reason.md -> implementation_repair_reason.json
agents/reason.md -> 02_repair_implementation_react/01_reason_repair/agents/reason_repair.md
02_observe_audit -> 02_repair_implementation_react/03_observe_repair
OBSERVE WORKFLOW observe_audit -> OBSERVE WORKFLOW observe_repair
REASON CODEX in top-level workflow -> REASON WORKFLOW reason_repair in repair workflow
```

- [ ] **Step 2: Tighten initial act unit prompt**

In `act_unit.md`, keep:

```text
只能读 `.lgwf/current_implementation_unit_context.json`
只能写 `workspace_output_files`
schema 只来自 `target_output_file_schemas`
不递归读 `.lgwf`
```

Remove wording that tells the initial unit to prioritize observe repair feedback.

- [ ] **Step 3: Run prompt contract tests**

Run:

```powershell
python -m unittest skills\lgwf-wf-tools\workflows\wf-create\tests\test_prompt_contracts.py
```

Expected: PASS.

---

### Task 9: Run Full Verification

**Files:**

- No source edits unless tests reveal stale references.

- [ ] **Step 1: Run full wf-create tests**

Run:

```powershell
python -m unittest discover skills\lgwf-wf-tools\workflows\wf-create\tests
```

Expected: all tests pass.

- [ ] **Step 2: Run compileall**

Run:

```powershell
python -m compileall -q skills\lgwf-wf-tools\workflows\wf-create
```

Expected: no output and exit code 0.

- [ ] **Step 3: Confirm old files are gone**

Run:

```powershell
Test-Path skills\lgwf-wf-tools\workflows\wf-create\wf\04_implement_steps_react\agents
Test-Path skills\lgwf-wf-tools\workflows\wf-create\wf\04_implement_steps_react\02_observe_audit
Test-Path skills\lgwf-wf-tools\workflows\wf-create\wf\04_implement_steps_react\scripts\initialize_implementation_observe.py
Test-Path skills\lgwf-wf-tools\workflows\wf-create\wf\04_implement_steps_react\scripts\decide_implementation.py
```

Expected: all four commands print `False`.

- [ ] **Step 4: Confirm no README files were reintroduced under implementation stage**

Run:

```powershell
Get-ChildItem -LiteralPath skills\lgwf-wf-tools\workflows\wf-create\wf\04_implement_steps_react -Recurse -Filter README.md
```

Expected: no output.

- [ ] **Step 5: Remove Python cache files created by tests**

Run:

```powershell
Get-ChildItem -LiteralPath skills\lgwf-wf-tools\workflows\wf-create -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force
```

Expected: no remaining `__pycache__` under `wf-create`.

---

## Self-Review

- Spec coverage: 覆盖了用户确认的两阶段结构：`01_implement_units` 首版 FOREACH，`02_repair_implementation_react` 专职修复优化 ReAct。
- OB 到 reason：`02` 先运行 `03_observe_repair` 写 `.lgwf/implementation_observe.json`，再进入 REASON，保证 reason 有反馈可读。
- Prompt 边界：repair spec 只在 `02_repair_implementation_react` 内，初版 act unit 不读 reason/observe。
- Path boundary：所有 workflow refs 使用本目录相对路径；slot 子 workflow 不使用 `..` 读取父目录资源，父级 ReAct 通过 `SPEC "agents/spec.md"` 承载共同准则。
- Test coverage: 包含 topology、prompt contract、schema registry、script unit tests、structure validator、full unittest 和 compileall。
