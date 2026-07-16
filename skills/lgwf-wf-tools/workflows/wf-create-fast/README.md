# lgwf-wf-create-fast

`lgwf-wf-create-fast` 是 `lgwf-wf-tools` 内部唯一对外可见、可启动的 workflow 创建器。它处理普通、简单和轻量 LGWF workflow 创建请求：前半段由 LGWF 固化需求和业务流，后半段把已落盘的 scaffold 交给主 agent；主 agent 必须先生成执行计划，再按计划完善实现和验证。

## 目录

```text
wf-create-fast/
  AGENTS.md
  README.md
  entry_contract.json
  tests/
  ws/
  wf/
    workflow.lgwf
    01_confirm_requirements/
    02_confirm_business_flow/
    03_materialize_scaffold/
    04_main_agent_handoff/
  self-improve/
```

## 阶段

1. `define_requirements`：确认目标 workflow 的需求，产出 `.lgwf/create_requirements.json`。
2. `design_structure`：复用业务流确认和 `scaffold_package`，产出 `.lgwf/business_flow.json` 与 `.lgwf/scaffold_package_result.json`。
3. `materialize_scaffold`：把 scaffold plan 转成真实目标 package 文件。
4. `main_agent_handoff`：生成包含 `plan_then_execute` 契约的 `.lgwf/main_agent_authoring_handoff.json`，通过 `HANDOFF` 交给主 agent 先生成执行计划，再按计划完善实现。

handoff 的 `target_package.materialization` 会保留 scaffold 创建和跳过的文件清单，主 agent 应据此汇报外部目标 package 写入；不能仅依据 run summary 的 workspace diff 判断是否产生目标文件。

## 与旧 `wf-create` 的差异

- 不生成 `step_designs.json`。
- 不执行步骤设计 structural gate。
- 不拆分 implementation units。
- 不做 repair ReAct。
- 不自动进入 `wf-post-fix`。
- 目标 package 的最终实现由主 agent 在 handoff 后先规划、再按计划完成。

## 主要产物

- `.lgwf/create_requirements.json`
- `.lgwf/business_flow.json`
- `.lgwf/scaffold_package_result.json`
- `.lgwf/materialize_scaffold_result.json`
- `.lgwf/main_agent_authoring_handoff.json`

## 验证

```powershell
python -m unittest discover skills\lgwf-wf-tools\workflows\wf-create-fast\tests
python skills\lgwf-wf-tools\vendor\lgwf-client-assist\scripts\lgwf.py audit skills/lgwf-wf-tools/workflows/wf-create-fast/wf/workflow.lgwf
python skills\lgwf-wf-tools\workflows\wf-create-fast\self-improve\scripts\self_improve.py eval
```

## 未覆盖范围

- 不负责生成完整最终 workflow 实现。
- 不负责自动运行目标 workflow。
- 不负责自动启动 `wf-post-fix`。
- 本轮不包含 `self-improve/`；后续可单独补齐。
