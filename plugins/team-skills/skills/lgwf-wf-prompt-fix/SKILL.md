---
name: lgwf-wf-prompt-fix
description: 验收并修复目标 LGWF workflow 引用的 prompt 文件。用于用户希望盘点 workflow prompt 引用、按 LGWF prompt 规范审查、选择要修复的 prompt 问题、执行 prompt 修复，并在运行或修复 workflow 前确认 prompt 验收结果。
---

# LGWF Workflow Prompt Fix

将本 skill 作为 `lgwf_wf_prompt_fix` 面向 Codex 的入口。实际修复逻辑在 `wf/workflow.lgwf` 中。

## 启动

始终通过 LGWF facade 启动：

```powershell
python <lgwf-client-assist>/scripts/lgwf.py run --workflow-lgwf plugins\team-skills\skills\lgwf-wf-prompt-fix\wf\workflow.lgwf --work-dir plugins\team-skills\skills\lgwf-wf-prompt-fix\ws --input-json "{\"prompt_fix_target\":{\"target_workflow_lgwf\":\"plugins\\team-skills\\skills\\lgwf-plan\\workflow.lgwf\",\"target_package_root\":\"plugins\\team-skills\\skills\\lgwf-plan\"}}" --background
```

启动时通过 `--input-json` 传入目标 workflow 信息；workflow 入口 `init_prompt_fix_target` 会先向当前对话请求确认，并在 approve 后初始化 work dir 输入：

- `.lgwf/prompt_fix_target.json`: 目标 workflow package metadata。

`--input-json` 必须包含 `prompt_fix_target` object；其中至少包含 `target_workflow_lgwf`，建议包含 `target_package_root` 和 `target_dirs`。主 agent 在 `init_prompt_fix_target` pending 时 approve 该 JSON 后，workflow 会持久化 `.lgwf/prompt_fix_target.json`，然后执行 `check_lgwf_client_assist`。如果当前 Codex 环境找不到已安装的 `lgwf-client-assist` skill，workflow 会在任何 prompt audit 或 repair 节点启动前退出，并报告缺失依赖。

## 运行处理

- 使用 `lgwf.py status` 和 `lgwf.py wait` 持续跟踪同一个 `lgwf_wf_prompt_fix` run。
- 当 workflow 询问要修复哪些 prompt issue 时，展示 audit summary，并让用户选择 issue 或跳过修复。
- 当 workflow 请求最终确认时，展示 prompt acceptance summary；用户 approve 后继续同一个 run。
- 除了通过本 workflow，不要修改 `.lgwf/` runtime artifacts。
- 启动命令或 workflow resources 中不要使用绝对路径。

## 输出

在固定 work dir 下查看这些产物：

- `.lgwf/prompt_acceptance/inventory.json`
- `.lgwf/prompt_fix_target.json`
- `.lgwf/prompt_acceptance/environment_check.json`
- `.lgwf/prompt_acceptance/audit.json`
- `.lgwf/prompt_acceptance/fix_selection.json`
- `.lgwf/prompt_acceptance/repair_plan.json`
- `.lgwf/prompt_acceptance/repair_review.json`
- `.lgwf/prompt_acceptance/summary.json`
- `.lgwf/prompt_acceptance/confirmation.json`
