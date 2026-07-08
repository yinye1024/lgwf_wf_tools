# 变更日志

## 2026-07-08 合并版

- 为 `lgwf-wf-tools` registry 管理的 workflow 补齐节点级 `CONTRACT` 和 package 级 `artifact_contracts.json`，明确 `.lgwf/`、`reports/` 与目标 package 文件的输入输出边界。
- 收口 `wf-dsl-upgrade`：根 workflow 恢复八阶段 `STEP WORKFLOW` 薄编排，入口契约统一到 `dsl_upgrade_target`，并补齐 runtime 子 workflow 输入兜底与 fake E2E 覆盖。
- 更新 bundled `lgwf-client-assist` 产物，内置 `lgwf 0.1.2` wheel，并同步 vendor manifest。
- 增强 doctor/deep doctor 可验证性，确保正式 workflow 源码 contract 与 registry 入口能被静态审计。
