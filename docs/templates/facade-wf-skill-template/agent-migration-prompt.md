# Agent 迁移指令模板

本文件用于让 agent 按 facade workflow skill 模式迁移现有仓库。推荐分两段使用：先设计，后实施。

## 第一段：只分析，不改文件

```text
请参考 <模板仓库路径>\docs\templates\facade-wf-skill-template
以及 <参考仓库路径>\skills\lgwf-wf-tools 的实际实现，
为 <目标仓库路径> 设计 facade + registry + workflow contract 迁移方案。

要求：
- 先读取目标仓库的 AGENTS.md、README.md、skills/、modules/、workflows/ 或等价目录。
- 识别当前对外 skill、业务模块、脚本、workflow、测试和运行状态目录。
- 判断哪些能力应成为 registry workflow，哪些只是共享规则或底层脚本。
- 提出目标目录结构、registry 条目、entry_contract 字段、迁移步骤、风险和最小验证命令。
- 保护现有 dirty worktree，不要改动文件，不要重排无关目录。
- 用中文输出方案。
```

本机示例：

```text
请参考 D:\allen\github\lgwf_wf_tools\docs\templates\facade-wf-skill-template
以及 D:\allen\github\lgwf_wf_tools\skills\lgwf-wf-tools 的实际实现，
为 D:\allen\github\sb_skills 设计 facade + registry + workflow contract 迁移方案。
先只分析现状、提出目标结构、迁移步骤、风险和最小验证方式，不要改文件。
```

## 第二段：按确认方案实施

```text
按刚才确认的迁移方案实施。

执行要求：
- 只修改方案列出的文件。
- 保留现有业务模块、脚本和用户未提交改动，不做无关重排。
- 优先新增 facade registry、entry_contract、共享规则和校验脚本。
- 每迁移一个 workflow id，就补齐 AGENTS.md、README.md、entry_contract.json 和最小验证。
- 需要运行 workflow 时，输入 JSON 使用 UTF-8 no BOM 文件，不直接把复杂 JSON 放进 PowerShell 参数。
- 遇到 approval、review、human_choice 或 waiting_human 时，必须展示确认原因、影响范围、待确认内容、可选决策、提交值、相关产物和后续动作。
- 每一步后运行最小验证，并汇报命令与结果。
```

## 对 agent 的检查点

迁移方案必须回答：

- facade skill 入口叫什么。
- 现有 skill 是否保留为薄包装，还是合并到 facade 路由。
- registry 中有哪些 workflow id。
- 每个 workflow id 是 `lgwf` 还是 `tool-workflow`。
- 每个 workflow 的输入字段、状态目录、主要产物和 resume 规则是什么。
- 哪些目录是源码，哪些目录是运行状态。
- 哪些操作需要用户确认。
- 最小验证命令是什么。

## 风险提示

- 不要把“参考 `lgwf-wf-tools`”理解为复制它的业务 workflow。
- 不要在目标仓库已有大量未提交变更时做目录大搬迁。
- 不要让多个 workflow 共享同一个 `.lgwf/` 状态目录。
- 不要把外部私有路径写成模板默认值。
