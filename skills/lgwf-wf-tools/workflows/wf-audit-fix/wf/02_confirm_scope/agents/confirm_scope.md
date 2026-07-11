# 确认 audit 修复目标范围

请按共享人工确认模板展示本次目标范围确认。这是范围审批，不是升级计划审批；本节点只决定是否允许当前 manifest 中的目标继续进入后续 FOREACH，不承诺任何具体修复策略。

必须覆盖：

- `mode`、`scope_mode` 和目标数量。
- 每个授权 `.lgwf` 的路径和 `pre_hash`。
- `validation.passed` 与失败原因。
- 目标来自 `.lgwf/target_manifest.json`，审批不会扩大 target_paths、不会追加 `allowed_dirs`，也不会把未授权文件加入本次 run。
- approve 只授权 manifest 中已通过校验的 `.lgwf` 进入 `FOREACH upgrade_each`；在 `mode=apply` 时，Codex 也只能修改当前 FOREACH item 暴露的授权 `.lgwf` 文件。
- `dry_run` 下只运行 audit 和汇总，不授权写入目标文件。
- reject 不是失败；它表示本次不修复目标文件，直接进入 summary，并在报告中记录跳过原因。

只允许提交 `approve` 或 `reject`。不要在审批提交中夹带新的目标路径、修复建议或规则变更；这些内容不会作为执行授权。
