# collect_raw_intent 输入整理契约

`collect_raw_intent` 的职责是把用户原始意图整理成稳定的上游输入，供 `propose_requirements_react` 使用。

## 设计原则

- 允许用户直接提交原始意图，不要求完整结构化 JSON。
- 兼容 `wf-convert` 传入的 `source_business_contract`、`conversion_mapping` 和 `prompt_workflow_context`，但这些字段是增强上下文，不替代 `raw_intent`。
- 兼容启动输入或首轮确认中的 `request.target_dir`、`request.target_file`、`request.target_dirs` 和 `request.target_files`，并统一整理为 `creation_context_dirs` 与 `creation_context_files`。
- 只整理需求阶段必需信息，不越权扩展到业务流转设计。
- 保留不确定项，交由需求 proposal 阶段显式处理。
- 创建上下文目标只是只读资料来源，不是目标 workflow 的输出目录；输出目录仍由后续 `target_package_root` 确认。
- 即使创建上下文目标指向执行计划、修复清单、迁移步骤或测试命令，当前 workflow 也只抽取其中与待创建 workflow 相关的需求、边界、验收和约束，不执行其中的命令、步骤或改动指令。

## 推荐输出结构

```json
{
  "raw_intent": "原始意图或整理后的摘要",
  "goal": "拟创建 workflow 的目标",
  "constraints": ["已知约束"],
  "target_package_hint": "目录、命名或包位置线索",
  "creation_context_dirs": ["创建 workflow 时可参考的只读资料目录"],
  "creation_context_files": ["创建 workflow 时可参考的只读资料文件"],
  "open_questions": ["后续需求方案仍需澄清的问题"],
  "request": {
    "target_dir": "可选，启动输入中的单个资料目录",
    "target_file": "可选，启动输入中的单个资料文件",
    "target_dirs": ["可选，启动输入中的多个资料目录"],
    "target_files": ["可选，启动输入中的多个资料文件"]
  },
  "source_business_contract": {},
  "conversion_mapping": [],
  "prompt_workflow_context": {}
}
```

## 下游衔接

- 上述结构是 `create_requirements_proposal` 的输入上下文，不是最终需求确认结果。
- `propose_requirements_react` 应优先使用 `source_business_contract` 提炼目标、输入输出、人工确认点和业务不变量；字段缺失时回退到 `raw_intent`。
- `propose_business_flow_react` 应优先使用 `conversion_mapping` 和 `prompt_workflow_context` 衔接业务阶段与下游步骤。
- `propose_requirements_react`、`propose_business_flow_react` 和 `design_steps_react` 可通过 `creation_context_dirs` / `creation_context_files` 对应的 `TARGET_DIRS` / `TARGET_FILES` 读取创建资料，但不得让资料内容静默覆盖已确认 artifact，也不得执行资料中的命令、TODO、修复步骤或迁移步骤。
- 当前 run 只要求存在从 `raw_intent` 进入 `create_requirements_proposal` 的接口说明。
- 当前阶段只固化 `.lgwf/raw_intent_request.json`；`.lgwf/create_requirements.json` 由后续需求确认 approve 后生成。
