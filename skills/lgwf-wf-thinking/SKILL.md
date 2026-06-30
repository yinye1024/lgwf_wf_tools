---
name: lgwf-wf-thinking
description: 用于把用户对 LGWF workflow 的创建、修复、转换、优化或治理需求转成可确认的组合方案，并在用户确认后交给 lgwf-wf-tools 执行。
---

# lgwf-wf-thinking

用于把用户对 LGWF workflow 的需求转成可确认的组合方案。适用场景包括创建、修复、转换、优化 workflow，或为 workflow 增加测试、治理和提示词改进流程。

## 使用方式

1. 先阅读本目录的 `AGENTS.md`。
2. 需要启动本 skill 自带 workflow 时，必须通过已注册的 `lgwf-wf-tools` 调用 `scripts/run_skill_workflow.py`。
3. 在组合方案生成前，必须读取当前可用的 workflow registry，优先使用相邻 skill `../lgwf-wf-tools/registry.json`。
4. `compose_plan` 必须作为 ReAct 节点运行，用观察、推理、行动、校验的循环生成高质量组合方案。
5. `confirm_plan` 只做确认和微调，不能绕过用户审批直接执行下游 workflow。
6. 用户确认后，输出面向 `lgwf-wf-tools` 的 handoff 指令包，由 `lgwf-wf-tools` 继续负责实际执行、审批代理、监控和 run handle 管理。

## 运行入口

在仓库根目录执行：

```powershell
python skills\lgwf-wf-tools\scripts\run_skill_workflow.py --workflow-lgwf skills\lgwf-wf-thinking\wf\workflow.lgwf --work-dir skills\lgwf-wf-thinking\ws --input-json "{}" --background
```

该命令由 `lgwf-wf-tools` 的代理脚本调用本 facade 内置的 `lgwf.py run`，外部 skill 不需要知道 bundled `lgwf.py` 的具体路径。需要传入 `raw_intent` 等业务输入时，应先准备 UTF-8 JSON 输入，再通过 `--input-json` 或 `--input-json-file` 传入。
