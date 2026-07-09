# validation_rules

- 打包产物必须保留 `wf/workflow.lgwf`。
- 打包产物根目录不能包含运行态 `.lgwf/`。
- `vendor/lgwf-client-assist/scripts/lgwf.py`、`scripts/run_local_lgwf_workflow.py` 和 `PACKAGING_MANIFEST.json` 必须存在。
- 若源 skill 存在 `wf/docs/steps/`，打包产物必须保留对应文档副本。
- `audit_smoke=true` 时必须执行 authoring audit；失败只形成诊断，不自动修复。

