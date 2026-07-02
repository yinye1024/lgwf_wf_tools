# Real Positive E2E 质量规范

真实正向 E2E 的职责是验证目标 workflow 在一个小而真实的业务场景中能完成正向闭环。它不承担全分支覆盖。

必须满足：

- 使用真实 Codex。
- 文件名不以 `test_` 开头，默认不被 `unittest discover` 收录；人工验收时直接执行测试文件。
- 不用环境变量控制是否允许运行真实 Codex。
- 业务 fixture 小、明确、可自动验收。
- 真实运行前必须执行或封装 `lgwf.py audit <target workflow.lgwf>`，audit 目标是原始目标 `workflow.lgwf`。
- 自动处理 approval。
- 最终使用黑盒断言验证业务产物。
- audit 失败、真实运行失败或超时时，保留 audit 输出、`.tmp` 或等价运行目录、fixture 和相关 artifact。

禁止：

- 被 `unittest discover` 或常规回归入口自动运行真实 Codex。
- 把失败/重试分支覆盖放进本测试。
- 只断言内部 `.lgwf` 状态而没有业务黑盒断言。
