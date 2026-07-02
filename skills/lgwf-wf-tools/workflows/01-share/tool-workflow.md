# Tool Workflow 规则

`tool-workflow` 是通过脚本、文档和人工确认执行的内部 workflow，不由 LGWF runtime 启动。

## 执行规则

- 执行前读取 `registry.json` 条目和目标 workflow 的 `AGENTS.md`。
- 使用 registry 中的 `entry` 作为主入口；命令参数以目标 workflow 文档为准。
- 只读诊断类命令可以直接执行。
- 会记录 incident、生成 proposal、生成 eval case 或修改发布包基线的命令，必须遵循目标 workflow 的人工确认边界。
- 运行期产物必须写入 `.local/` 下的约定目录，不得写入发布包基线，除非用户明确批准 promote 或发布包变更。
