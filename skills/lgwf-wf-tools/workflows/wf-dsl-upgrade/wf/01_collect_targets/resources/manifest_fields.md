# target_manifest 字段约定

- `request`：归一化后的入口请求。
- `targets`：逐目标的原始路径、resolved path、授权结果、失败原因和 pre-hash。
- `authorized_targets`：后续阶段允许消费的唯一目标清单。
- `validation`：范围校验摘要。
