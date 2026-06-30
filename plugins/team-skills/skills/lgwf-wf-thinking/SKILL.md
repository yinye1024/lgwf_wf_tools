---
name: lgwf-wf-thinking
description: 用于把用户对 LGWF workflow 的创建、修复、转换、优化或治理需求转成可确认的组合方案，并在用户确认后交给 lgwf-wf-tools 执行。
---

# lgwf-wf-thinking

用于把用户对 LGWF workflow 的需求转成可确认的组合方案。适用场景包括创建、修复、转换、优化 workflow，或为 workflow 增加测试、治理和提示词改进流程。

## 使用方式

1. 先阅读本目录的 `AGENTS.md`。
2. 读取并运行内置 workflow：`wf/workflow.lgwf`，工作目录使用 `ws/`。
3. 在组合方案生成前，必须读取当前可用的 workflow registry，优先使用相邻 skill `../lgwf-wf-tools/registry.json`。
4. `compose_plan` 必须作为 ReAct 节点运行，用观察、推理、行动、校验的循环生成高质量组合方案。
5. `confirm_plan` 只做确认和微调，不能绕过用户审批直接执行下游 workflow。
6. 用户确认后，输出面向 `lgwf-wf-tools` 的 handoff 指令包，由 `lgwf-wf-tools` 继续负责实际执行、审批代理、监控和 run handle 管理。

## 运行入口

在仓库根目录执行：

```powershell
python plugins/team-skills/skills/lgwf-wf-tools/vendor/lgwf-client-assist/scripts/lgwf.py run plugins/team-skills/skills/lgwf-wf-thinking/wf/workflow.lgwf --work-dir plugins/team-skills/skills/lgwf-wf-thinking/ws --input-json "{\"raw_intent\":\"描述你的 workflow 需求\"}"
```

如果 `ws/.lgwf` 已存在，应先检查当前 session 状态，再决定 resume、rerun 或保留现场。
