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

通过 facade 内置 `lgwf-client-assist` 运行。日常运行直接使用固定 vendor 路径：

```powershell
$lgwfPy = "plugins\team-skills\skills\lgwf-wf-agent\vendor\lgwf-client-assist\scripts\lgwf.py"
python $lgwfPy run --workflow-lgwf plugins\team-skills\skills\lgwf-wf-agent\workflows\wf-prompt-fix\wf\workflow.lgwf --work-dir plugins\team-skills\skills\lgwf-wf-agent\workflows\wf-prompt-fix\ws --input-json "{\"prompt_fix_target\":{\"target_workflow_lgwf\":\"plugins\\team-skills\\skills\\lgwf-plan\\wf\\workflow.lgwf\",\"target_package_root\":\"plugins\\team-skills\\skills\\lgwf-plan\\wf\"}}" --background
```

workflow 会先执行 `init_prompt_fix_target`，等待主 agent 在当前对话确认目标 JSON；确认后再执行 `check_lgwf_client_assist`，确认本地 bundled client 可用。

`check_lgwf_client_assist` 还会把 prompt 验收所需的最小 bundled client reference 运行时复制到 `.lgwf/prompt_acceptance/reference_context/`。这是临时运行上下文，不是源码副本；源码仍只维护 facade 的 `vendor/lgwf-client-assist/`。

## 输出

主要产物写入 work dir：

- `.lgwf/prompt_fix_target.json`
- `.lgwf/prompt_acceptance/environment_check.json`
- `.lgwf/prompt_acceptance/reference_context/AGENTS.md`
- `.lgwf/prompt_acceptance/reference_context/prompt-assist/*.md`
- `.lgwf/prompt_acceptance/inventory.json`
- `.lgwf/prompt_acceptance/audit.json`
- `.lgwf/prompt_acceptance/fix_selection.json`
- `.lgwf/prompt_acceptance/repair_plan.json`
- `.lgwf/prompt_acceptance/repair_review.json`
- `.lgwf/prompt_acceptance/summary.json`
- `.lgwf/prompt_acceptance/confirmation.json`
