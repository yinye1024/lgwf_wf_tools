# inspection 质量门禁

## 模块定位

本子 workflow 是 `inspect_prompt_workflow_react` 的复合 Observe，只负责审查 `.lgwf/prompt_workflow_inspection.json`。它不是 registry workflow，也不是独立 Codex skill。

## 入口

- workflow：`workflow.lgwf`
- 调用方：`../workflow.lgwf` 中的 `OBSERVE WORKFLOW inspection_quality_gate`

## 依赖

- `.lgwf/prompt_file_index.json`
- `.lgwf/prompt_workflow_inspection.json`
- `wf/shared/scripts/observe_protocol.py`

## 状态边界与产物

运行状态只写入当前 `wf-convert` work dir 的 `.lgwf/`：

- `.lgwf/prompt_workflow_inspection_observe_py.json`
- `.lgwf/prompt_workflow_inspection_observe_codex.json`
- `.lgwf/prompt_workflow_inspection_observe.json`

## 验证

```powershell
python -m unittest discover skills\lgwf-wf-tools\workflows\wf-convert\tests
python skills\lgwf-wf-tools\vendor\lgwf-client-assist\scripts\lgwf.py audit skills\lgwf-wf-tools\workflows\wf-convert\wf\workflow.lgwf
```

## 禁止事项

- Python Observe 不判断证据语义是否成立。
- Codex Observe 不重复字段、类型、路径或枚举检查。
- Codex Observe 不生成 canonical `verdict`。
- 本子 workflow 不修改 inspection、源 prompt workflow 或目标 package。
