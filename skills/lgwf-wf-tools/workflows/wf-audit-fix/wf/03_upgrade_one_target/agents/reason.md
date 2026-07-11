# 生成当前 DSL audit 修正方案

本 slot 不修改文件。请读取当前目标 `.lgwf`、`state.wf_audit_fix.current_audit.diagnostics`、`state.wf_audit_fix.repair_observation`、`state.wf_audit_fix.repair_decision` 和 `.lgwf/current_target_context.json`，逐条 diagnostics 生成 act 可直接执行的修正方案。

输出要求：

- 逐条列出 diagnostic 的 code、location、message。
- 对每条 diagnostic 给出具体修正方案，说明要修改哪个节点、添加或移动哪段 DSL。
- 遇到 `LGWF_CONTRACT_REQUIRED_MISSING` 时，方案必须是补齐对应节点的 `CONTRACT`；没有业务 I/O 的节点使用 `CONTRACT {}`。
- 如果多条 diagnostics 指向同一节点，合并成一次节点级修改方案。
- 如果 `repair_decision.status` 是 `no_progress`，或 `repair_observation.changed=false` 且 `diagnostic_delta=0`，必须说明上一轮方案为什么没有生效，并给出不同的具体修法；不得重复上一轮相同方案。
- 如果 `diagnostic_delta < 0`，优先处理剩余 diagnostics，不要回滚已降低 diagnostic 数量的改动。
- 如果 diagnostics identity 发生变化，先说明新增、消失和保留的 diagnostics，再针对保留和新增项给方案。
- 不修改文件，不新增文件，不运行命令。

修正方案必须保持原 workflow 的节点 id、节点顺序、脚本路径、prompt 路径和业务流程。
