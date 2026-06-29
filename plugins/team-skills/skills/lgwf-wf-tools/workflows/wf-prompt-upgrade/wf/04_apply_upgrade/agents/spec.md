# Prompt Upgrade Apply Spec

`apply_prompt_upgrade` 只负责执行用户已经确认的 prompt 升级方案。它不得重新扩大升级范围，不得处理未批准的 `prompt_upgrades[]`。

## ReAct Contract

- `REASON` 读取 `proposal.json` 和 `decision.json`，为已批准升级生成 `.lgwf/prompt_upgrade/apply_plan.json`。
- `ACT` 严格按 `apply_plan.json` 修改目标 workflow package 内的文件。
- `OBSERVE` 复核已批准升级是否落地，写 `.lgwf/prompt_upgrade/apply_review.json`。

## Constraints

- 只能修改目标 workflow package 内、已批准升级涉及的文件。
- 不修改 `.lgwf/` runtime artifacts，除本 workflow 指定的 `.lgwf/prompt_upgrade/*.json`。
- 默认不修改 `lgwf_wf_prompt_upgrade` 自身文件；只有当 `target_package_root` 明确指向本 workflow package，且批准的升级项列出了相关文件时，才允许修改自身 prompt。
- 如果发现 proposal 与目标文件现状冲突，停止对应升级项并写入 review，不要擅自扩大范围。
- 复核必须按 `apply_plan.steps[]` 逐项核对实际变更，并记录计划外文件、缺失变更和未执行步骤。
