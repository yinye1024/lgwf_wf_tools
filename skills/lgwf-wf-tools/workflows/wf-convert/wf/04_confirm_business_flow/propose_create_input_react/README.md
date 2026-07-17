# propose_create_input_react

## 模块定位

本目录自包含 `wf-create-fast` 创建输入 proposal ReAct 的私有文件。父阶段只在 `workflow.lgwf` 中声明 ReAct 拓扑，不从 inspection ReAct 目录读取私有 prompt、脚本或 Observe 内部报告；跨 ReAct 只消费父级声明的 canonical artifact。

## Slot 对应

- `agents/spec.md`：ReAct `SPEC`。
- `agents/reason.md`：`REASON CODEX` slot。
- `agents/act.md`：`ACT CODEX` slot。
- `agents/observe.md`：复合 `OBSERVE` 中的 Codex 语义检查 slot。
- `scripts/decide.py`：`DECIDE PY` slot，只读取 canonical Observe。

## Observe 子流程

`ob.lgwf` 是本 ReAct 的 Observe 子流程，依次执行 `scripts/validate.py`、`agents/observe.md` 和 `scripts/merge.py`。

- 输入：`.lgwf/prompt_workflow_inspection.json`、`.lgwf/wf_create_fast_input_proposal.json`。
- 中间产物：`.lgwf/wf_create_fast_input_observe_py.json`、`.lgwf/wf_create_fast_input_observe_codex.json`。
- canonical 输出：`.lgwf/wf_create_fast_input_observe.json`。

## 验证

```powershell
python -m unittest discover skills\lgwf-wf-tools\workflows\wf-convert\tests
python skills\lgwf-wf-tools\vendor\lgwf-client-assist\scripts\lgwf.py audit skills\lgwf-wf-tools\workflows\wf-convert\wf\workflow.lgwf
```

## 禁止事项

- 不读取 inspection ReAct 目录下的私有 prompt、脚本或 Observe 中间报告。
- Decide 不读取 proposal 业务产物或单个 observer 报告。
- Python Observe 不判断自然语言语义，Codex Observe 不重复确定性检查。
- 不在本目录创建更深层 workflow。
