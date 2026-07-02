# classify_risk

根据 amount 和 risk_level 计算 route_hint。

规则：

- amount < 1000 且 risk_level == low，route_hint 为 auto_approve。
- amount >= 1000 或 risk_level == high，route_hint 为 human_review。
- 字段缺失时 route_hint 为 needs_revision。

