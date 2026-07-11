---
name: facade-template
description: 作为 facade workflow skill 的统一入口；根据用户意图路由到 registry 中的内部 workflow 或 tool workflow。
---

# Facade Template

本 skill 是 facade 入口，只做最小第一跳：显式维护命令读取 `docs/maintenance.md`；其他 workflow 意图读取同目录 `AGENTS.md`，由 registry 路由到目标 workflow。

## 使用场景

- 用户调用本 facade 的帮助、列表、诊断或维护命令。
- 用户要求运行、继续、创建、修复、测试、查询、整理或优化目标业务流程。
- 用户要求对已注册 workflow 做 self-improve、复盘、proposal 或发布前检查。

## 第一跳

- 显式维护命令读取 [docs/maintenance.md](docs/maintenance.md)。
- workflow 意图读取 [AGENTS.md](AGENTS.md)，再按 `registry.json` 选择目标 workflow。
- 创建、转换、修复或优化模块时，先读取 [workflows/01-share/module-contract.md](workflows/01-share/module-contract.md)。

## 启动输入保护

- PowerShell 中不要把复杂 JSON 直接传给 `--input-json`。
- 包含中文、引号、换行或嵌套结构时，先写 UTF-8 no BOM JSON 文件，再使用 `--input-json-file <path>`。
- 启动 registry 内部 LGWF workflow 时优先使用 `python scripts\run_skill_workflow.py --workflow-id <id> --input-json-file <path>`。

## 人工确认展示约束

- 遇到 `approval`、`review`、`human_choice`、`waiting_human` 或子 workflow 代理确认时，必须读取 [workflows/01-share/approval.md](workflows/01-share/approval.md)。
- 不得只用一句话询问是否确认；必须展示确认原因、影响范围、待确认内容、可选决策、提交值、相关产物和后续动作。

## 显式指令

| 指令 | 下一步 |
| --- | --- |
| `/facade-template` | 读取 [docs/maintenance.md](docs/maintenance.md)。 |
| `/facade-template help` | 读取 [docs/maintenance.md](docs/maintenance.md)。 |
| `/facade-template list` | 运行 `python scripts\list_workflows.py`。 |
| `/facade-template doctor` | 运行 `python scripts\validate_registry.py`。 |

## 暴露边界

- 只暴露根目录 `SKILL.md` 作为 Codex skill。
- `workflows/*` 是内部 workflow package 或 tool workflow，不作为独立 Codex skill。
- `workflows/01-share/` 是共享规则目录，不注册为 workflow。
- runtime 或 vendor 由目标仓库按需接入，不属于本模板必备内容。
