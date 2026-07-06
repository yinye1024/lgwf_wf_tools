# lgwf-wf-convert 工作流指引

本目录是 `lgwf-wf-tools/workflows/wf-convert` 下的内部 workflow package，由 facade 根目录 `registry.json` 派发，不作为独立 Codex skill 注册。

## 模块契约

- 模块类型：`lgwf_workflow_package`。
- 执行前必须读取 `../01-share/module-contract.md`、`../01-share/registry-contract.md`、`../01-share/lgwf-dispatch.md`、`../01-share/lgwf-monitor.md`、`../01-share/approval.md` 和 `../01-share/artifacts.md`。
- 入口字段、输入示例和 `--auto-human` 策略以本目录 `entry_contract.json` 为准；本文件只解释业务纪律和运行边界。
- 转换输出交给 `wf-create` 时，目标模块必须继续满足 `module-contract.md` 的自包含契约。

## 目标

`wf-convert` 面向 prompt workflow 转换场景：读取现有 prompt workflow 目录，分析 prompt、agent、resource 和说明文件，产出可交给 `wf-create` 的创建输入包、源业务契约、转换映射、业务一致性报告与转换报告。

第一版不直接生成最终目标 LGWF workflow，但会在转换输入通过人工确认后，通过 `RUN_WORKFLOW` 启动 `wf-create`。结束时会通过 `HANDOFF` 引导用户选择是否对刚创建的 workflow 启用 `wf-post-fix`，但不自动调用 `wf-prompt-fix`、`wf-prompt-upgrade`、`wf-fix` 或 `wf-post-fix`。

`wf-convert` 先通过 `map_wf_create_input` 把 `state.lgwf_wf_convert.wf_create_payload` 映射为 `state.lgwf_wf_convert.wf_create_input`，再通过原生 `RUN_WORKFLOW wf_create` 节点启动下游 `wf-create`，并由 `capture_wf_create_result` 消费运行结果。随后 `verify_business_parity` 基于 `source_business_contract`、`conversion_mapping` 和创建结果生成 `.lgwf/business_parity_report.json`，`summarize_result` 输出转换报告，`prepare_post_fix_handoff` 从刚创建的 workflow 信息和一致性报告生成 `wf-post-fix` 输入文件，`handoff_wf_post_fix` 暴露 pending action 给主 agent 等待用户确认。

## 目录边界

- 真实 workflow package root：`wf/`
- workflow 入口：`wf/workflow.lgwf`
- work dir：`ws/`
- 运行状态只允许写入 `ws/.lgwf`
- 目标 package 根目录不得写入 `.lgwf`

## 输入契约

推荐输入：

```json
{
  "prompt_convert_target": {
    "target_dir": "skills/example-prompt-workflow",
    "entry_files": ["README.md"],
    "target_workflow_name": "example-workflow",
    "target_package_root": "skills/example-workflow"
  }
}
```

## 固定产物

- `.lgwf/prompt_convert_target.json`
- `.lgwf/prompt_file_index.json`
- `.lgwf/prompt_workflow_inspection.json`
- `.lgwf/wf_create_input_proposal.json`
- `.lgwf/wf_create_input_approval.json`
- `.lgwf/wf_create_input.json`
- `.lgwf/wf_create_payload.json`
- `.lgwf/wf_create_input_for_wf_create.json`
- `.lgwf/business_parity_report.json`
- `.lgwf/post_fix_handoff_input.json`
- `reports/convert-workflow/convert_result_report.md`
- `state.lgwf_wf_convert.wf_create_input`
- `state.lgwf_wf_convert.wf_create_result`
- `state.lgwf_wf_convert.wf_create_result_summary`
- `state.lgwf_wf_convert.business_parity_report`
- `state.lgwf_wf_convert.post_fix_handoff_payload`
- `state.lgwf_wf_convert.post_fix_handoff`

## 下游 `wf-create`

转换完成后，`wf-convert` 使用：

- `WORKFLOW "workflows/wf-create/wf/workflow.lgwf"`
- `WORK_DIR "workflows/wf-create/ws"`
- `INPUT state.lgwf_wf_convert.wf_create_input`
- `RESULT state.lgwf_wf_convert.wf_create_result`

`wf-create` 自身仍保留需求、业务流和步骤设计的人工确认边界。

`wf-convert` 传给 `wf-create` 的输入保持 `raw_intent` 兼容，同时在可用时附带 `source_business_contract`、`conversion_mapping` 和 `prompt_workflow_context`。下游缺少结构化字段时仍按旧的 `raw_intent` 输入运行。

## 下游 `wf-post-fix` handoff

`wf-convert` 结束时使用 `HANDOFF handoff_wf_post_fix` 暴露：

- `workflow_id`: `wf-post-fix`
- `workflow_lgwf`: `skills/lgwf-wf-tools/workflows/wf-post-fix/wf/workflow.lgwf`
- `work_dir`: `skills/lgwf-wf-tools/workflows/wf-post-fix/ws`
- `input_json_file`: 当前 work dir 下的 `.lgwf/post_fix_handoff_input.json`
- `business_parity_report`: 当前转换的一致性审查摘要；若 verdict 不是 `pass`，主 agent 应优先向用户说明缺失业务规则或审批点。

主 agent 必须向用户展示该 pending action，并在用户明确确认后才运行建议命令。

## 最小验证

```powershell
python -m unittest discover skills\lgwf-wf-tools\workflows\wf-convert\tests
python skills\lgwf-wf-tools\vendor\lgwf-client-assist\scripts\lgwf.py audit skills\lgwf-wf-tools\workflows\wf-convert\wf\workflow.lgwf
```
