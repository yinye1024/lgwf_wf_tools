# 交接给主 agent 启动 wf-create-fast

你正在接手 `wf-convert` 的后续动作。`wf-convert` 已完成 prompt workflow 分析、转换 proposal 确认，并生成了 `wf-create-fast` 的输入。

## 必须执行

- 读取 `.lgwf/wf_create_fast_handoff.json`。
- 读取其中的 `input_json_file`，默认是 `.lgwf/wf_create_fast_input_for_wf_create_fast.json`。
- 使用该输入启动 `wf-create-fast` 创建目标 workflow package。
- 优先使用 facade runner：`python skills/lgwf-wf-tools/scripts/run_skill_workflow.py --workflow-id wf-create-fast --input-json-file <input_json_file>`。

## 禁止事项

- 不要在 `wf-convert` 内继续实现目标 package。
- 不要启动 `wf-create`。
- 不要生成 `.lgwf/step_designs.json`。
- 不要调用标准 `wf-create` 的 03/04 implementation 链路。
- 不要自动启动 `wf-post-fix`。

如果启动前发现输入不足，做保守假设，并在最终说明中列出。
