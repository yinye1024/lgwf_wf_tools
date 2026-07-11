# 执行当前目标的 DSL 修复

请执行 reason 给出的修正方案，只修改 `TARGET_FILES` 中的当前 `.lgwf` 文件。

要求：

- 每处改动都必须对应当前 audit diagnostic 或 reason 中合并后的节点级方案。
- `LGWF_CONTRACT_REQUIRED_MISSING` 必须通过补齐对应节点 `CONTRACT` 修复；没有业务 I/O 的节点写 `CONTRACT {}`。
- 保持原 workflow 业务顺序、节点 id、脚本和 prompt 引用不变。
- 不要修改运行态 `.lgwf/`、`ws/`、`reports/` 文件。
- 不要生成临时文件、报告或额外说明文件。
- 完成后简要说明执行 reason 的哪些修正方案，以及对应的 diagnostic code。
