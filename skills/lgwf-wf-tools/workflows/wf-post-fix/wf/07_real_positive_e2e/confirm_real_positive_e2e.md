# 是否运行真实正向 E2E

即将运行：`real_positive_e2e`

作用：执行真实 Codex 正向链路，验证目标 workflow 在真实模型参与下能完成业务闭环。

可能影响：会调用真实 Codex，耗时和成本都高于 fake 测试；即使已经选择 `auto`，本阶段仍必须单独确认。

跳过影响：不验证真实模型参与下的业务闭环。

请选择并提交 JSON：`{"decision":"run|skip|auto|stop","reason":"..."}`。

`stop` 会让当前子 workflow 直接 `FAIL_ALL` 并终止整个 post-fix 运行。
