# main_agent_handoff 阶段

本阶段生成 `.lgwf/main_agent_authoring_handoff.json`，再通过 runtime `HANDOFF` 发布 `next_action=main_agent_authoring` 的 pending action。主 agent 收到 pending action 后先提交 `handoff submit` ack，再读取 handoff 中的两个 confirmed artifact 文件、`target_package` 和 `execution_contract`。在首次修改目标 package 前，主 agent 必须先生成执行计划，随后按计划实施、更新进度并完成验证。

## 输入

- `.lgwf/create_requirements.json`
- `.lgwf/business_flow.json`
- `.lgwf/scaffold_package_result.json`
- `.lgwf/materialize_scaffold_result.json`

## 输出

- `.lgwf/main_agent_authoring_handoff.json`
- `state.lgwf_wf_create_fast.main_agent_handoff_payload`
- `state.lgwf_wf_create_fast.main_agent_handoff`

`main_agent_authoring_handoff.json` 必须包含：

- `confirmed_requirements`
- `confirmed_business_flow`
- `target_package`
- `execution_contract`

其中 `confirmed_requirements` 指向 `.lgwf/create_requirements.json`，`confirmed_business_flow` 指向 `.lgwf/business_flow.json`；`execution_contract` 固化 `plan_then_execute` 顺序，要求计划先于任何目标文件编辑；`target_package.materialization` 汇总 scaffold 实际创建和跳过的文件，供主 agent 在最终说明中报告外部目标写入。`scaffold_package_result` 和 `materialize_scaffold_result` 只作为本阶段内部组装依据，不直接暴露给主 agent。

## 边界

- runtime `HANDOFF` 只用于通知主 agent 接手，不启动下游 workflow。
- 主 agent 必须使用 `handoff submit` ack，不能手工改 `.lgwf/handoff/*.pending.json`。
- 主 agent 在首次编辑目标 package 前必须生成执行计划；实施中按计划更新状态，发生偏离时先更新计划。
- 不自动启动 `wf-post-fix`。
- 不自动运行目标 workflow。
- 不生成 `step_designs.json`。

## 验证

```powershell
python -m unittest skills\lgwf-wf-tools\workflows\wf-create-fast\tests\test_main_agent_handoff.py
```
