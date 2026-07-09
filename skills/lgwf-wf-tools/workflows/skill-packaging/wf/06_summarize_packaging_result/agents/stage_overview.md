# 06_summarize_packaging_result

本阶段负责把确认计划、执行摘要与验证结论汇总成最终说明。

- 只读取 `.lgwf/confirmed_packaging_plan.json`、`.lgwf/materialized_package.json`、`.lgwf/package_validation.json`。
- 只输出 `.lgwf/packaging_result_summary.json` 与 `reports/skill-packaging/packaging_result_report.md`。
- 不自动触发任何下游 workflow。

