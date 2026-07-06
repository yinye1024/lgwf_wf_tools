---
name: wf-audit-fix
description: 用于对目标 LGWF workflow 执行静态 audit、candidate 修复、promote 和真实目录复检闭环；不运行目标 workflow 业务。
---

# wf-audit-fix

本 skill 面向“只修复 LGWF DSL / audit 静态问题”的场景。它提供独立 Codex skill 入口，内嵌 LGWF workflow 位于 `wf/workflow.lgwf`，运行状态写入同级 `ws/.lgwf/`。

## 使用场景

- 用户要求修复某个 `workflow.lgwf` 的 authoring audit 失败。
- 用户明确只需要静态 DSL / audit 修复，不需要运行目标 workflow 业务。
- 用户需要在隔离 candidate 副本中修复，确认通过后再 promote 回真实目录并复检。

## 第一跳

执行前读取同目录 `AGENTS.md`，确认模块边界、状态目录和验证方式。

## 运行入口

启动内嵌 workflow 时，通过 `lgwf-wf-tools` 的代理脚本调用：

```powershell
python skills\lgwf-wf-tools\scripts\run_skill_workflow.py --workflow-lgwf skills\wf-audit-fix\wf\workflow.lgwf --work-dir skills\wf-audit-fix\ws --input-json-file <input.json> --background
```

输入 JSON 至少包含：

```json
{
  "target_workflow_lgwf": "D:/path/to/workflow.lgwf",
  "max_attempts": 5
}
```

## 禁止事项

- 不通过 `lgwf-wf-tools` registry 派发本 workflow。
- 不运行目标 workflow 业务。
- 不处理目标 workflow 自身 approval。
- 不在源码根目录写入 `.lgwf`。
