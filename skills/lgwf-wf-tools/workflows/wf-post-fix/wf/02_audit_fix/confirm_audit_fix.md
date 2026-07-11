# 是否运行 wf-audit-fix

即将运行：`wf-audit-fix`

作用：扫描目标 workflow package 授权范围内的 `.lgwf` 文件，运行 authoring audit，并按 diagnostics 做最小修复，包括缺失 `CONTRACT`、读写消费链和 DSL 静态诊断。

可能影响：`mode=apply` 且目标范围确认通过后，可能修改目标 workflow package 内被 manifest 授权的 `.lgwf` 文件；子 workflow 内部仍会请求目标范围确认。

跳过影响：后续 prompt 修复、prompt 升级和 E2E 生成可能基于未通过 audit 的 DSL 继续执行，子 workflow 缺失 contract 或消费链问题会继续残留。

请选择并提交 JSON：

```json
{"decision":"run","reason":"运行当前阶段"}
```

`decision` 可选：`run`、`skip`、`auto`、`stop`。`auto` 表示从当前阶段开始自动运行后续可自动阶段；`stop` 会让当前子 workflow 直接 `FAIL_ALL` 并终止整个 post-fix 运行。
