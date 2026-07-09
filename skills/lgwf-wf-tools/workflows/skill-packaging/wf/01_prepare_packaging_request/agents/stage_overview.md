# prepare-packaging-request

## Role
你是输入规范化阶段说明文档，负责解释本阶段如何把启动输入整理成稳定 `packaging_request`，并在真实写入前冻结路径边界。

## Inputs
- workflow 启动输入中的 `packaging_request`
- `resources/packaging_request.schema.json`
- `wf/shared/scripts/packaging_common.py`

## Task
1. 规范化 `source_skill`、`output_parent`、`runtime_source`、`force` 和 `audit_smoke`。
2. 把路径解析结果写入 `.lgwf/packaging_request.json` 与 `.lgwf/packaging_path_context.json`。
3. 冻结允许写入范围，确保后续阶段不会越界写入。

## Success Criteria
- `packaging_request` 字段完整且可被预检阶段直接消费。
- 绝对路径只保留在运行时产物，不进入 authoring 资源路径。
- 输出目录边界在真实写入前已经显式化。

## Output
本阶段只写 `.lgwf/` 状态产物，不写真实打包输出目录。
