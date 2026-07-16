# main_agent_handoff 阶段

本阶段生成 `.lgwf/main_agent_authoring_handoff.json`，并通过 `HANDOFF` 把已确认需求、业务流、scaffold plan 和已落盘目标目录交给主 agent。

## 输入

- `.lgwf/create_requirements.json`
- `.lgwf/business_flow.json`
- `.lgwf/scaffold_package_result.json`
- `.lgwf/materialize_scaffold_result.json`

## 输出

- `.lgwf/main_agent_authoring_handoff.json`
- `state.lgwf_wf_create_fast.main_agent_handoff_payload`
- `state.lgwf_wf_create_fast.main_agent_handoff`

## 边界

- 不自动启动 `wf-post-fix`。
- 不自动运行目标 workflow。
- 不生成 `step_designs.json`。

## 验证

```powershell
python -m unittest skills\lgwf-wf-tools\workflows\wf-create-fast\tests\test_main_agent_handoff.py
```
