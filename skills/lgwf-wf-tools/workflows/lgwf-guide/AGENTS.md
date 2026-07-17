# LGWF 入门引导

本目录是 `lgwf-wf-tools` facade 下的内部 `tool_workflow`，通过普通对话帮助用户提出合适的问题，快速了解 LGWF 和 `lgwf-wf-tools`。它不是 LGWF runtime workflow，不包含 `workflow.lgwf`，不得作为独立 Codex skill 注册。

## 模块定位

- 模块类型：`tool_workflow`。
- 目标：默认先从“为什么要用 LGWF，而不是继续使用现有 prompt 工作流”切入，再通过“最小 workflow 完整演示”和“`workflow.lgwf` 核心语法”建立执行与阅读直觉；随后提供状态、人工确认、失败恢复和组件关系四个进阶问题。
- 边界：只在当前对话中提供引导，不运行 LGWF、不创建状态、不修改文件。
- 具体提问路径和回复规则以 `../../docs/lgwf-guide.md` 为准。

## 入口

- Registry id：`lgwf-guide`。
- Registry kind：`tool-workflow`。
- Entry：`docs/lgwf-guide.md`。
- Entry contract：`workflows/lgwf-guide/entry_contract.json`。
- 显式命令：`/lgwf-wf-tools guide`、`/lgwf-wf-tools learn`、`/lgwf-wf-tools 入门`。
- 默认入口：用户只调用 `/lgwf-wf-tools`，入口预检通过且没有给出具体任务。
- 自然语言触发：用户希望快速了解 LGWF、学习如何提问或了解 `lgwf-wf-tools`，且尚未进入具体创建、运行、修复或治理任务。

## 依赖

- 读取 `../../README.md`、`../../AGENTS.md` 和 `../../registry.json` 理解 facade 与当前可用模块。
- 解释 LGWF、DSL 或 runtime 时，按需读取 `../../vendor/lgwf-client-assist/AGENTS.md` 及其路由到的 reference，不复制整套文档。
- 遵循 `../01-share/module-contract.md`、`../01-share/registry-contract.md` 和 `../01-share/tool-workflow.md`。
- 用户进入具体任务后，回到 facade 根 `AGENTS.md` 选择目标模块。

## 状态边界

- 不创建 `.lgwf/`、`.local/`、session、报告或缓存。
- 不写目标 workflow、facade 源码或 vendor 文件。
- 上下文只保留在当前对话中；后续提问按当前对话自然继续。

## 产物

- 三个优先核心问题、四个进阶问题及一次性提问模板。
- 用户选择后的补充问题路径。
- 基于当前仓库文件和命令的简明解释。
- 一个建议的下一问题或既有模块入口。
- 不生成文件产物或 handoff payload。

## 执行规则

1. 用户已经提出具体问题时，直接回答，不强制展示完整菜单。
2. 用户只有宽泛学习意图时，完整展示 `../../docs/lgwf-guide.md` 中的“三个优先核心问题 + 四个进阶问题”、一次性提问模板和优先顺序提示；不先要求用户选择抽象的学习方向。
3. 用户回复问题序号或直接复制问题后，优先回答该问题，结尾最多推荐一个自然衔接的下一问题，避免一次倾倒全部资料。
4. 回答当前仓库的能力、路径或命令时，先读取对应事实源；示例必须与当前 registry 和 bundled client 一致。
5. 用户明确要求执行创建、运行、修复、测试或治理任务时，结束引导并回到根 `AGENTS.md` 路由；不得在本模块中替代目标模块执行。
6. 只有实际完成入口 doctor 预检时才说明“预检已通过”；直接调用 `guide`、`learn`、`入门` 或自然语言触发时不得虚构预检结果。
7. 回答第一问时必须同时说明 LGWF 的增益边界和不适用场景；如果现有 prompt 工作流已经简单、稳定、无需持久状态或人工门禁，应明确说明可以继续使用，不得把引导写成单向推广。

## 验证

```powershell
python skills\lgwf-wf-tools\scripts\validate_registry.py
python -m unittest discover skills\lgwf-wf-tools\tests -p "test_lgwf_guide.py"
python -m unittest discover skills\lgwf-wf-tools\tests -p "test_registry_workflow_paths.py"
```

## 禁止事项

- 不得创建或启动 `workflow.lgwf`。
- 不得调用 `scripts/run_skill_workflow.py` 或 vendor `scripts/lgwf.py run`。
- 不得因为用户想了解某个具体操作就自动执行该操作。
- 不得把静态记忆当作当前仓库事实；涉及现有命令、模块和路径时必须先读取对应文件。
- 不得把内部 `lgwf-guide` 注册为独立 Codex skill。
