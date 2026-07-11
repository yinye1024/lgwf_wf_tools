# Facade Workflow Skill 通用模板

本模板用于把一个 Codex skill 或多 skill 仓库整理成 `facade + registry + workflow contract` 模式。它抽取自 `skills/lgwf-wf-tools` 的结构，但不包含任何业务 workflow，也不复制 vendor runtime。

## 适用场景

- 一个仓库里已有多个 skill、脚本或 workflow，需要统一入口。
- 需要让 agent 先路由用户意图，再启动目标 workflow 或 tool workflow。
- 需要用机器可读 `registry.json` 和 `entry_contract.json` 固化输入、状态、产物和恢复规则。
- 需要迁移现有仓库，但不希望一次性大重排目录。

不适合的场景：

- 只有一个很小脚本，没有长期维护、审批、恢复或自我治理需求。
- 目标仓库没有稳定业务边界，暂时还不能定义 workflow id。
- 只是想复制 `lgwf-wf-tools` 的具体业务流程。

## 目录

```text
facade-wf-skill-template/
  README.md
  agent-migration-prompt.md
  migration-guide.md
  adaptation-notes.md
  skeleton/
    SKILL.md
    AGENTS.md
    README.md
    registry.json
    docs/
    workflows/
    scripts/
    tests/
```

## 使用方式

1. 先阅读 `agent-migration-prompt.md`，让 agent 对目标仓库输出迁移方案，不要直接改文件。
2. 迁移方案确认后，把 `skeleton/` 复制到目标 facade skill 目录。
3. 替换 `facade-template`、`example-workflow`、`example-tool-workflow` 等示例名称。
4. 按目标仓库实际能力补齐 `registry.json` 和各 workflow 的 `entry_contract.json`。
5. 运行模板内 `scripts/validate_registry.py` 和目标仓库既有测试。

## 设计原则

- `SKILL.md` 只做最小第一跳。
- `AGENTS.md` 负责自然语言路由。
- `registry.json` 是唯一 workflow 注册表。
- `entry_contract.json` 是 runner 和 agent 的机器可读接口。
- `workflows/01-share/` 只放共享规则，不注册为 workflow。
- `workflows/<id>/` 才是可派发模块。
- 运行状态必须和源码分离，默认使用 `ws/.lgwf/`。
- 模板不包含 vendor runtime；目标仓库自行决定使用 bundled runtime、外部 runner 或已有 runtime。

## 验证

在当前仓库检查模板结构：

```powershell
python docs\templates\facade-wf-skill-template\tests\test_template_structure.py -v
python docs\templates\facade-wf-skill-template\skeleton\tests\test_registry_template.py -v
```

在复制后的目标仓库检查 registry：

```powershell
python scripts\validate_registry.py
python scripts\list_workflows.py
```

## 禁止事项

- 不要把内部 workflow 注册成独立 Codex skill。
- 不要把业务规则复制到每个 `SKILL.md`。
- 不要让 workflow 运行状态写入源码目录。
- 不要自动提交 approval 或跳过用户确认。
- 不要在模板中硬编码某个本机路径、外部仓库或用户 vault。
