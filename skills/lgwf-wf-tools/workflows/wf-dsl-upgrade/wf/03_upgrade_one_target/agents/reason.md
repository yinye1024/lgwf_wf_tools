# 生成当前 DSL audit 修正方案

本 slot 不修改文件。请读取当前目标 `.lgwf`、`state.wf_dsl_upgrade.current_audit.diagnostics` 和 `.lgwf/current_target_context.json`，逐条 diagnostics 生成 act 可直接执行的修正方案。

输出要求：

- 逐条列出 diagnostic 的 code、location、message。
- 对每条 diagnostic 给出具体修正方案，说明要修改哪个节点、添加或移动哪段 DSL。
- 遇到 `LGWF_CONTRACT_REQUIRED_MISSING` 时，方案必须是补齐对应节点的 `CONTRACT`；没有业务 I/O 的节点使用 `CONTRACT {}`。
- 如果多条 diagnostics 指向同一节点，合并成一次节点级修改方案。
- 不修改文件，不新增文件，不运行命令。

修正方案必须保持原 workflow 的节点 id、节点顺序、脚本路径、prompt 路径和业务流程。
