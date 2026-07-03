# 是否运行 wf-fix 正向 E2E

即将运行：`wf_fix_positive_e2e`

作用：执行生成的 wf-fix 正向修复入口，验证失败后能否由 `wf-fix` 闭环修复。

可能影响：会启动 `wf-fix` 修复链路，可能修改目标 workflow package；即使已经选择 `auto`，本阶段仍必须单独确认。

跳过影响：不验证目标 workflow 的 wf-fix 修复闭环。

请选择并提交 JSON：`{"decision":"run|skip|auto|stop","reason":"..."}`。

`stop` 会让当前子 workflow 直接 `FAIL_ALL` 并终止整个 post-fix 运行。
