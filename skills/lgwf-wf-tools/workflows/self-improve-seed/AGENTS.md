# Self Improve Seed Workflow

本目录是 `lgwf-wf-tools` facade 下的内部 `tool-workflow`，职责是把 self-improve 的通用模式安装到目标 workflow package，使目标 workflow 获得自包含的自我提升结构。

它不是 LGWF runtime workflow，不包含固定 `workflow.lgwf`，不得作为独立 Codex skill 注册。

## 共用规则

执行本 workflow 前必须读取：

- `../01-share/AGENTS.md`
- `../01-share/module-contract.md`
- `../01-share/registry-contract.md`
- `../01-share/tool-workflow.md`
- `../01-share/artifacts.md`
- `../../docs/self-improve-seed.md`

模块类型：`tool_workflow`。本模块的入口、依赖、状态边界、产物、验证和禁止事项以本文件后续章节和 `../../docs/self-improve-seed.md` 为准。

入口参数、输入示例和 auto-human 适用性以本目录 `entry_contract.json` 为准；本文件只解释业务纪律和运行边界。

## 触发规则

- 用户要求把 self-improve 功能加到某个 workflow。
- 用户要求给目标 workflow 构造自包含 self-improve 结构。
- 用户要求目标 workflow 具备 incident、proposal、eval、trace-eval、check、scorecard 等类似自我进化能力。

## 执行入口

```powershell
python workflows/self-improve-seed/scripts/seed_self_improve.py --target <workflow-package>
```

生成后的目标 workflow 可运行：

```powershell
python self-improve/scripts/self_improve.py eval
python self-improve/scripts/self_improve.py trace-eval
python self-improve/scripts/self_improve.py check
```

## 产物边界

- 只写目标 workflow package 下的 `self-improve/` 和 `.local/self-improve/`。
- 默认不覆盖已有 `self-improve/`。
- 生成后的目标 workflow 不依赖本 facade 的 `workflows/self-improve/` 脚本。
- `trace-eval` 只做 runtime smoke evidence，不生成业务 golden case。
