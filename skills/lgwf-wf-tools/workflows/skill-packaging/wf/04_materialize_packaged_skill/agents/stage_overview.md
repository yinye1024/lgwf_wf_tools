# 04_materialize_packaged_skill

本阶段负责在人工确认后的范围内执行真实打包。

- 只读取 `.lgwf/confirmed_packaging_plan.json` 与 `.lgwf/packaging_preflight.json`。
- 真实副作用限定为批准后的 `output_parent/<source-skill-name>/`。
- 不在本阶段做自动修复、自动重试或 post-fix handoff。
- 运行摘要最终写入 `.lgwf/materialized_package.json`，供验证阶段消费。

