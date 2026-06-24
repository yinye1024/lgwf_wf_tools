# LGWF Workflow Prompt Fix

`lgwf_wf_prompt_fix` 用于验收并修复目标 LGWF workflow package 中被 `PROMPT` 或 `PROMPT_REF` 引用的 prompt 文件。它只负责 prompt 验收、问题选择、修复和复核，不负责运行目标 workflow。

## 输入

启动时通过 `--input-json` 传入目标 workflow 信息：

- `target_workflow_lgwf`: 目标 `workflow.lgwf` 路径，必填。
- `target_package_root`: 目标 workflow package 根目录，可选，默认使用 `target_workflow_lgwf` 所在目录。
- `target_dirs`: Codex 审计和修复可分析的目标目录，可选，默认使用 `target_package_root`。

workflow 会在入口节点 `init_prompt_fix_target` 请求确认，并在 approve 后初始化：

- `.lgwf/prompt_fix_target.json`: 目标 workflow 的路径和 package 信息。

## 运行

通过 `lgwf-client-assist` facade 运行：

```powershell
python <lgwf-client-assist>/scripts/lgwf.py run --workflow-lgwf plugins\team-skills\skills\lgwf-wf-prompt-fix\wf\workflow.lgwf --work-dir plugins\team-skills\skills\lgwf-wf-prompt-fix\ws --input-json "{\"prompt_fix_target\":{\"target_workflow_lgwf\":\"plugins\\team-skills\\skills\\lgwf-plan\\workflow.lgwf\",\"target_package_root\":\"plugins\\team-skills\\skills\\lgwf-plan\"}}" --background
```

workflow 会先执行 `init_prompt_fix_target`，等待主 agent 在当前对话确认目标 JSON；确认后再执行 `check_lgwf_client_assist`。如果当前 Codex 环境未安装 `lgwf-client-assist` skill，workflow 会在 prompt audit 或 repair 节点启动前失败并给出原因。

## 输出

主要产物写入 work dir：

- `.lgwf/prompt_fix_target.json`
- `.lgwf/prompt_acceptance/environment_check.json`
- `.lgwf/prompt_acceptance/inventory.json`
- `.lgwf/prompt_acceptance/audit.json`
- `.lgwf/prompt_acceptance/fix_selection.json`
- `.lgwf/prompt_acceptance/repair_plan.json`
- `.lgwf/prompt_acceptance/repair_review.json`
- `.lgwf/prompt_acceptance/summary.json`
- `.lgwf/prompt_acceptance/confirmation.json`
