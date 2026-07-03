# wf-post-fix 后续处理交接

当前 `wf-convert` 已完成 prompt workflow 转换，并通过 `wf-create` 生成了目标 LGWF workflow。请向用户展示刚创建的目标 workflow、`wf-post-fix` 输入文件、建议命令和关键产物，并询问是否启用 `wf-post-fix` 对刚创建的 workflow 执行后处理。

不要自动启动下游 workflow。只有用户明确确认后，主 agent 才能运行 pending action 中的 `suggested_command` 或等价的 `lgwf.py run` 命令。
