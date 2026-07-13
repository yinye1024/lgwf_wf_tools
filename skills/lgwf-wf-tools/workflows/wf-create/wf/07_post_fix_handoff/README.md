# post-fix handoff 阶段

本阶段负责在 `wf-create` 完成结果汇总后，准备并暴露 `wf-post-fix` 的人工确认交接。它是 `wf-create` 根 workflow 的最后一个子 workflow，不自动启动下游 workflow。

## 入口

- workflow：`wf/07_post_fix_handoff/workflow.lgwf`
- 入口节点：`prepare_post_fix_handoff`
- 被父级调用：`wf/workflow.lgwf` 的 `STEP post_fix_handoff`
- 局部产物契约：`wf/07_post_fix_handoff/artifact_contracts.json`

## 输入

- `state.lgwf_wf_create.summary_result`
- `.lgwf/create_result_summary.json`，仅当 stdin 未传入有效 summary 时作为回退来源

## 产物

- `state.lgwf_wf_create.post_fix_handoff_payload`
- `state.lgwf_wf_create.post_fix_handoff`
- `.lgwf/post_fix_handoff_input.json`

## 边界

- 只生成 handoff payload 和 `wf-post-fix` 输入文件。
- 只通过 `HANDOFF handoff_wf_post_fix` 暴露 pending action。
- 不自动执行 `wf-post-fix`，必须等待用户确认。

## 验证

```powershell
python -m unittest skills\lgwf-wf-tools\workflows\wf-create\tests\test_state_handoff_contracts.py
```
