# 05_verify_packaged_skill

本阶段只做结构化验证，不做自动修复。

- 校验打包输出目录结构、manifest、embedded runtime 和 runner 指向。
- `audit_smoke=true` 时，对打包产物中的 `wf/workflow.lgwf` 执行 authoring audit。
- 最终把验证结果写入 `.lgwf/package_validation.json`。

