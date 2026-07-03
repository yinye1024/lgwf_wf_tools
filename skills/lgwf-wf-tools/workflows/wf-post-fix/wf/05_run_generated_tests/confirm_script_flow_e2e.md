# 是否运行脚本级 E2E

即将运行：`script_flow_e2e`

作用：执行生成的脚本级 E2E，验证目标 workflow 的脚本分支、route 分支和状态 artifact 契约。

可能影响：只运行 Python 自动化测试，不启动目标 LGWF runtime，不调用真实 Codex。

跳过影响：无法确认脚本级测试入口是否真的可运行。

请选择并提交 JSON：`{"decision":"run|skip|auto|stop","reason":"..."}`。

`stop` 会让当前子 workflow 直接 `FAIL_ALL` 并终止整个 post-fix 运行。
