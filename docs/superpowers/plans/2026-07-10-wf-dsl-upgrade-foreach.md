# wf-dsl-upgrade FOREACH 重构 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `wf-dsl-upgrade` 从批量规则迁移器重构为“目录收集目标后用 `FOREACH` 逐个 workflow 修复”的工作流。

**Architecture:** 根 `wf/workflow.lgwf` 只做收集、确认、`FOREACH` 调度和汇总；单个 `.lgwf` 的 audit、Codex 修复、复检和结果固化放入 `wf/03_upgrade_one_target/workflow.lgwf`。Python 负责确定性收集、audit、授权校验、route 和 summary；Codex 只负责根据 audit diagnostics 做语义修复。

**Tech Stack:** LGWF authoring DSL、`subgraph.foreach`、`subgraph.react`、Python `unittest`、现有 `dsl_upgrade_common.py` helper。

---

### Task 1: 结构测试

**Files:**
- Modify: `D:\allen\github\lgwf_wf_tools\skills\lgwf-wf-tools\workflows\wf-dsl-upgrade\tests\test_upgrade_pipeline_logic.py`

- [ ] **Step 1: 写失败测试**

新增测试断言根 workflow 包含 `FOREACH upgrade_each`、使用 `FAIL collect`、调用 `03_upgrade_one_target/workflow.lgwf`，并断言 per-target 子 workflow 存在 `REACT repair_target`。

- [ ] **Step 2: 运行测试确认失败**

Run:

```powershell
python -m unittest skills\lgwf-wf-tools\workflows\wf-dsl-upgrade\tests\test_upgrade_pipeline_logic.py
```

Expected: FAIL，因为现有根 workflow 仍是 batch/classify/build/apply 结构。

### Task 2: 目标列表状态输出

**Files:**
- Modify: `D:\allen\github\lgwf_wf_tools\skills\lgwf-wf-tools\workflows\wf-dsl-upgrade\wf\01_collect_targets\scripts\collect_targets.py`
- Modify: `D:\allen\github\lgwf_wf_tools\skills\lgwf-wf-tools\workflows\wf-dsl-upgrade\wf\01_collect_targets\workflow.lgwf`
- Test: `D:\allen\github\lgwf_wf_tools\skills\lgwf-wf-tools\workflows\wf-dsl-upgrade\tests\test_upgrade_pipeline_logic.py`

- [ ] **Step 1: 写失败测试**

新增测试调用 collect 逻辑，断言 stdout/state update 包含 `wf_dsl_upgrade.targets`，每个 item 包含 `target_id`、`path`、`allowed_dirs` 和 `mode`。

- [ ] **Step 2: 运行测试确认失败**

Run:

```powershell
python -m unittest discover skills\lgwf-wf-tools\workflows\wf-dsl-upgrade\tests
```

Expected: FAIL，因为当前 collect 只写 manifest 文件，不提供 foreach state list。

- [ ] **Step 3: 最小实现**

让 collect 脚本继续写现有 manifest，同时输出 LGWF state update：`{"wf_dsl_upgrade": {"targets": [...]}}`。目标 item 只携带 per-target workflow 必需字段，不把大体积 audit 结果塞入 state。

### Task 3: FOREACH 根编排

**Files:**
- Modify: `D:\allen\github\lgwf_wf_tools\skills\lgwf-wf-tools\workflows\wf-dsl-upgrade\wf\workflow.lgwf`
- Create: `D:\allen\github\lgwf_wf_tools\skills\lgwf-wf-tools\workflows\wf-dsl-upgrade\wf\02_confirm_scope\workflow.lgwf`
- Create scripts under `wf\02_confirm_scope\scripts\`

- [ ] **Step 1: 写失败测试**

测试 root DSL audit 可解析 `FOREACH`，并且 reject/summary 仍可结束。

- [ ] **Step 2: 最小实现**

根流程变为 `collect_targets -> confirm_scope -> upgrade_each -> summarize_upgrade_result`。确认阶段只确认目标范围，使用二元 `APPROVAL`，不再确认空升级计划。

### Task 4: 单目标修复子 workflow

**Files:**
- Create: `D:\allen\github\lgwf_wf_tools\skills\lgwf-wf-tools\workflows\wf-dsl-upgrade\wf\03_upgrade_one_target\workflow.lgwf`
- Create: `wf\03_upgrade_one_target\agents\repair_spec.md`
- Create: `wf\03_upgrade_one_target\agents\reason.md`
- Create: `wf\03_upgrade_one_target\agents\act.md`
- Create scripts under `wf\03_upgrade_one_target\scripts\`

- [ ] **Step 1: 写失败测试**

测试子 workflow audit 通过，且包含 `prepare_repair_context`、`audit_current_target`、`REACT repair_target MAX 3`、`finalize_target`。

- [ ] **Step 2: 最小实现**

子 workflow 读取 `state.wf_dsl_upgrade.current_target`，先 audit；若已通过则 finalize；否则进入 ReAct。`OBSERVE PY` 复跑 audit 并做授权校验，`DECIDE PY` 根据 audit 是否通过决定 stop/retry/manual。

### Task 5: 文档和验证

**Files:**
- Modify: `D:\allen\github\lgwf_wf_tools\skills\lgwf-wf-tools\workflows\wf-dsl-upgrade\AGENTS.md`
- Modify: `D:\allen\github\lgwf_wf_tools\skills\lgwf-wf-tools\workflows\wf-dsl-upgrade\README.md`
- Modify: `D:\allen\github\lgwf_wf_tools\skills\lgwf-wf-tools\workflows\wf-dsl-upgrade\entry_contract.json`

- [ ] **Step 1: 更新中文文档**

说明 `FOREACH` 调度、per-target repair loop、Python/Codex 职责边界、`FAIL collect` 汇总语义。

- [ ] **Step 2: 全量验证**

Run:

```powershell
python -m unittest discover skills\lgwf-wf-tools\workflows\wf-dsl-upgrade\tests
$env:PYTHONPATH='D:\allen\github\lgwf\src'; D:\allen\github\lgwf\.venv\Scripts\python.exe -m lgwf_dsl.cli audit D:\allen\github\lgwf_wf_tools\skills\lgwf-wf-tools\workflows\wf-dsl-upgrade\wf\workflow.lgwf
```

Expected: tests OK，audit passed。
