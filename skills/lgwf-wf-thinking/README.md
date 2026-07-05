# lgwf-wf-thinking

`lgwf-wf-thinking` 是独立 Codex skill package，用于先识别 LGWF workflow 需求、形成组合方案，再把确认后的 handoff 交给 `lgwf-wf-tools` 执行。

## 模块类型

- `codex_skill`
- 内嵌 `lgwf_workflow_package`，入口为 `wf/workflow.lgwf`

## 入口

本 skill 通过 `SKILL.md` 触发。运行自带 workflow 时必须经由已注册的 `lgwf-wf-tools` 代理：

```powershell
python skills\lgwf-wf-tools\scripts\run_skill_workflow.py --workflow-lgwf skills\lgwf-wf-thinking\wf\workflow.lgwf --work-dir skills\lgwf-wf-thinking\ws --input-json-file <path>
```

## 依赖

- 读取 `skills/lgwf-wf-tools/registry.json` 获取当前可用 workflow 能力。
- 不直接执行下游 workflow；只生成 handoff 指令包。

## 状态与产物

- 运行状态写入 `skills/lgwf-wf-thinking/ws/.lgwf/`。
- 主要产物是需求分类、组合方案、用户确认记录和 handoff payload。

## 验证

```powershell
python skills/lgwf-wf-tools/vendor/lgwf-client-assist/scripts/lgwf.py audit skills/lgwf-wf-thinking/wf/workflow.lgwf
```
