# 是否运行 e2e-test-generator

即将运行：`e2e-test-generator`

作用：为目标 workflow 生成脚本级、runtime fake、真实正向和 wf-fix 正向四类 E2E 测试入口。

可能影响：会新增或刷新目标 workflow 测试目录中的 E2E 文件，并生成报告。

跳过影响：后续测试运行阶段可能找不到新生成的测试入口，只能记录跳过或失败。

请选择并提交 JSON：`{"decision":"run|skip|auto|stop","reason":"..."}`。

`stop` 会让当前子 workflow 直接 `FAIL_ALL` 并终止整个 post-fix 运行。
