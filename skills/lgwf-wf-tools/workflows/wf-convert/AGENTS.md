# lgwf-wf-convert 工作流指引

本目录是 `lgwf-wf-tools/workflows/wf-convert` 下的内部 workflow package，由 facade 根目录 `registry.json` 派发，不作为独立 Codex skill 注册。

## 目标

`wf-convert` 面向 prompt workflow 转换场景：读取现有 prompt workflow 目录，分析 prompt、agent、resource 和说明文件，产出可交给 `wf-create` 的创建输入包与转换报告。

第一版不直接生成最终目标 LGWF workflow，但会在转换输入通过人工确认后，通过 `RUN_WORKFLOW` 启动 `wf-create`。不自动调用 `wf-prompt-fix`、`wf-prompt-upgrade` 或 `wf-fix`。

`wf-convert` 完成转换报告后先通过 `map_wf_create_input` 把 `state.lgwf_wf_convert.wf_create_payload` 映射为 `state.lgwf_wf_convert.wf_create_input`，再通过原生 `RUN_WORKFLOW wf_create` 节点启动下游 `wf-create`，并由 `capture_wf_create_result` 消费运行结果。

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
- `.lgwf/wf_create_payload.json`
- `.lgwf/wf_create_input_for_wf_create.json`
- `reports/convert-workflow/convert_result_report.md`
- `state.lgwf_wf_convert.wf_create_input`
- `state.lgwf_wf_convert.wf_create_result`
- `state.lgwf_wf_convert.wf_create_result_summary`

## 下游 `wf-create`

转换完成后，`wf-convert` 使用：

- `WORKFLOW "workflows/wf-create/wf/workflow.lgwf"`
- `WORK_DIR "workflows/wf-create/ws"`
- `INPUT state.lgwf_wf_convert.wf_create_input`
- `RESULT state.lgwf_wf_convert.wf_create_result`

`wf-create` 自身仍保留需求、业务流和步骤设计的人工确认边界。

## 最小验证

```powershell
python -m unittest discover skills\lgwf-wf-tools\workflows\wf-convert\tests
python skills\lgwf-wf-tools\vendor\lgwf-client-assist\scripts\lgwf.py audit skills\lgwf-wf-tools\workflows\wf-convert\wf\workflow.lgwf
```
