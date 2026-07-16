# wf-create-fast 输入质量门禁

## 模块定位

本子 workflow 是 `propose_create_input_react` 的复合 Observe，只负责审查 `.lgwf/wf_create_fast_input_proposal.json`。它不是 registry workflow，也不是独立 Codex skill。

## 入口

- workflow：`workflow.lgwf`
- 调用方：`../workflow.lgwf` 中的 `OBSERVE WORKFLOW create_input_quality_gate`

## 依赖

- `.lgwf/prompt_workflow_inspection.json`
- `.lgwf/wf_create_fast_input_proposal.json`
- `wf/shared/scripts/observe_protocol.py`

## 状态边界与产物

运行状态只写入当前 `wf-convert` work dir 的 `.lgwf/`：

- `.lgwf/wf_create_fast_input_observe_py.json`
- `.lgwf/wf_create_fast_input_observe_codex.json`
- `.lgwf/wf_create_fast_input_observe.json`

## 验证

```powershell
python -m unittest discover skills\lgwf-wf-tools\workflows\wf-convert\tests
python skills\lgwf-wf-tools\vendor\lgwf-client-assist\scripts\lgwf.py audit skills\lgwf-wf-tools\workflows\wf-convert\wf\workflow.lgwf
```

## 禁止事项

- Python Observe 不判断自然语言意图是否充分。
- Codex Observe 不重复字段、类型、路径、枚举或覆盖率检查。
- Codex Observe 不生成 canonical `verdict`。
- 本子 workflow 不修改 proposal，不替人工确认作决定。
