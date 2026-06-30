# confirm_prompt_fix_target

请确认 prompt-fix 目标 workflow 信息。返回 JSON object，至少包含 `target_workflow_lgwf`；建议包含 `target_package_root` 和 `target_dirs`。

确认后，workflow 会只在指定目标 package 和 `target_dirs` 范围内盘点、审计并按后续人工选择修复 prompt。
