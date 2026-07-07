# lgwf-wf-tools

`lgwf-wf-tools` 是 facade 型 Codex skill，负责 LGWF workflow 的统一入口、路由、运行、审批展示、诊断、创建、修复、转换、测试生成和自我优化。

## 模块类型

- `codex_skill`
- facade skill，内部 workflow 由 `registry.json` 管理

## 入口

```text
/lgwf-wf-tools
/lgwf-wf-tools help
/lgwf-wf-tools init
/lgwf-wf-tools doctor
/lgwf-wf-tools list
/lgwf-wf-tools run <path>
/lgwf-wf-tools self-improve
```

自然语言的 workflow 创建、修复、转换、测试生成和优化请求会先进入 `AGENTS.md`，再由 `registry.json` 路由到内部 workflow。

## 依赖

- 内置 `vendor/lgwf-client-assist/` 作为 LGWF client。
- 内部 workflow 共享 `workflows/01-share/` 下的规则文档。

## 状态与产物

- facade 本地运行记录写入 `.local/`。
- `doctor --deep` 诊断报告写入 `.local/doctor/latest.md`、`.local/doctor/latest.json` 和 `.local/doctor/runs/<timestamp>/`。
- 内部 LGWF workflow 的运行状态写入各自 registry `work_dir` 下的 `.lgwf/`。
- 内部 `tool_workflow` 按自身 `AGENTS.md` 写入 `.local/`、目标 package 或约定输出目录。

## 验证

```powershell
python skills\lgwf-wf-tools\scripts\doctor_lgwf_wf_tools.py
python skills\lgwf-wf-tools\scripts\doctor_lgwf_wf_tools.py --deep
python -m unittest discover skills\lgwf-wf-tools\tests
```
