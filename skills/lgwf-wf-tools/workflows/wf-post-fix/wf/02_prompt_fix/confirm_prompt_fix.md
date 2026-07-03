# 是否运行 wf-prompt-fix

即将运行：`wf-prompt-fix`

作用：检查并修复目标 workflow 引用的 prompt 基础契约问题，包括缺失文件、引用不清、输入输出契约不完整、上下文约束不足等。

可能影响：可能修改目标 workflow package 内的 prompt 文件；子 workflow 内部遇到修复选择或应用确认时仍会请求你的确认。

跳过影响：后续 prompt upgrade 和 E2E 生成可能基于未清理的 prompt 问题继续执行。

请选择并提交 JSON：

```json
{"decision":"run","reason":"运行当前阶段"}
```

`decision` 可选：`run`、`skip`、`auto`、`stop`。`auto` 表示从当前阶段开始自动运行后续可自动阶段；`stop` 会让当前子 workflow 直接 `FAIL_ALL` 并终止整个 post-fix 运行。
