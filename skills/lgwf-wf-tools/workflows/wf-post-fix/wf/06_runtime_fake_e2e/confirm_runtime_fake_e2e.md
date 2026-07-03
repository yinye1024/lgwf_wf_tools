# 是否运行 runtime fake E2E

即将运行：`runtime_fake_e2e`

作用：执行生成的 fake Codex runtime E2E，验证 LGWF runtime 编排、状态文件和 fake response 契约。

可能影响：会启动真实 LGWF runtime，但 Codex runner 使用 fake，不调用真实 Codex。

跳过影响：无法确认 runtime 编排和 fake 契约是否通过。

请选择并提交 JSON：`{"decision":"run|skip|auto|stop","reason":"..."}`。

`stop` 会让当前子 workflow 直接 `FAIL_ALL` 并终止整个 post-fix 运行。
