# 静态审批路由 prompt workflow 编排

## 入口

- 入口阶段：`intake_request`
- 初始上下文：`artifacts/request_input.txt`
- agent prompt 根目录：`agents/`

## 阶段

### 1. intake_request

- Prompt：`agents/intake_request.md`
- 目标：读取审批请求，提取申请人、金额、风险等级和用途。
- 输入：`artifacts/request_input.txt`
- 输出：结构化审批请求摘要。

### 2. classify_risk

- Prompt：`agents/classify_risk.md`
- 目标：根据金额、风险等级和用途判断风险分类。
- 输入：`intake_request` 的结构化摘要。
- 输出：风险分类、触发规则和需要人工复核的原因。

### 3. decide_route

- Prompt：`agents/decide_route.md`
- 目标：根据业务规则决定审批路由。
- 输入：审批请求摘要和风险分类。
- 输出：`auto_approve`、`human_review` 或 `needs_revision`，并记录 reason 和 audit trail。

## 流程

```text
intake_request
-> classify_risk
-> decide_route
```

## 核心业务规则

- 金额小于 1000 且风险等级为 `low` 时自动通过。
- 金额大于等于 1000 或风险等级为 `high` 时进入人工复核。
- 所有路径都必须记录 audit trail。

## 非目标

- 不在 prompt workflow 内执行真实审批系统调用。
- 不直接生成 LGWF workflow package。
