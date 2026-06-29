# collect_raw_intent 输入整理契约

`collect_raw_intent` 的职责是把用户原始意图整理成稳定的上游输入，供 `propose_requirements_react` 使用。

## 设计原则

- 允许用户直接提交原始意图，不要求完整结构化 JSON。
- 只整理需求阶段必需信息，不越权扩展到业务流转设计。
- 保留不确定项，交由需求 proposal 阶段显式处理。

## 推荐输出结构

```json
{
  "raw_intent": "原始意图或整理后的摘要",
  "goal": "拟创建 workflow 的目标",
  "constraints": ["已知约束"],
  "target_package_hint": "目录、命名或包位置线索",
  "open_questions": ["后续需求方案仍需澄清的问题"]
}
```

## 下游衔接

- 上述结构是 `create_requirements_proposal` 的输入上下文，不是最终需求确认结果。
- 当前 run 只要求存在从 `raw_intent` 进入 `create_requirements_proposal` 的接口说明。
- 当前阶段只固化 `.lgwf/raw_intent_request.json`；`.lgwf/create_requirements.json` 由后续需求确认 approve 后生成。
