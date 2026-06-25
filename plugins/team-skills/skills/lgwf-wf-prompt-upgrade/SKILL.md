---
name: lgwf-wf-prompt-upgrade
description: 为目标 LGWF workflow 引用的 prompt 生成设计升级方案，经人工确认后应用升级。用于 prompt 已完成基础规范检查后，进一步提升 spec、角色职责、输出契约、质量指标和上下游对齐能力。
---

# LGWF Workflow Prompt Upgrade

将本 skill 作为 `lgwf_wf_prompt_upgrade` 的 Codex 入口。它不替代 `lgwf-wf-prompt-fix` 的规范检查；它专门处理“prompt 设计是否足够强、是否能驱动高质量结果”的升级方案和确认后改造。

## 启动

始终通过 LGWF facade 启动：

```powershell
python <lgwf-client-assist>/scripts/lgwf.py run --workflow-lgwf plugins\team-skills\skills\lgwf-wf-prompt-upgrade\wf\workflow.lgwf --work-dir plugins\team-skills\skills\lgwf-wf-prompt-upgrade\ws --input-json "{\"prompt_upgrade_target\":{\"target_workflow_lgwf\":\"plugins\\team-skills\\skills\\lgwf-plan\\workflow.lgwf\",\"target_package_root\":\"plugins\\team-skills\\skills\\lgwf-plan\"}}" --background
```

`--input-json` 必须包含 `prompt_upgrade_target` object；其中至少包含 `target_workflow_lgwf`，建议包含 `target_package_root` 和 `target_dirs`。入口 approval 会先让主 agent 确认该 JSON，然后持久化为 `.lgwf/prompt_upgrade_target.json`。

## 职责

- 盘点目标 workflow 引用的 prompt 文件。
- 分析 prompt 的设计职责、上下游契约、失败模式和升级机会。
- 生成结构化升级方案，并先交给用户确认。
- 用户 approve 后，只按确认方案修改目标 workflow package 内的相关 prompt/source 文件。
- 输出升级摘要，供主 agent 决定是否继续运行规范检查、验收或目标 workflow。

## 输出

- `.lgwf/prompt_upgrade/inventory.json`
- `.lgwf/prompt_upgrade/analysis.json`
- `.lgwf/prompt_upgrade/proposal.json`
- `.lgwf/prompt_upgrade/proposal_review.json`
- `.lgwf/prompt_upgrade/decision.json`
- `.lgwf/prompt_upgrade/apply_plan.json`
- `.lgwf/prompt_upgrade/apply_review.json`
- `.lgwf/prompt_upgrade/summary.json`
- `.lgwf/target_prompt_upgrade_summary.json`

