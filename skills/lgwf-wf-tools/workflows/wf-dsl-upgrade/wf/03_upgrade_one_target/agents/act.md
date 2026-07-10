# 执行当前目标的最小 DSL 修复

请根据上一轮分析和当前 audit diagnostics 修改目标 `.lgwf`。每处改动对应一个明确的 diagnostic 或上一轮 reason 中说明的最小修复点。

要求：

- 只修改 `TARGET_FILES` 中的当前 `.lgwf` 文件。
- 优先修复 audit 明确指出的问题。
- 补 `CONTRACT` 时只声明真实跨节点状态或 workspace artifact 边界；没有业务 I/O 的节点写 `CONTRACT {}`。
- 保持原 workflow 业务顺序、节点 id、脚本和 prompt 引用不变，除非 audit 明确要求。
- 不要修改运行态 `.lgwf/`、`ws/`、`reports/` 文件，也不要生成临时文件。
- 如果无法把改动精确对应到 diagnostic，不要猜测修复；保留现状并说明需要人工处理。

完成后简要说明改了什么和为什么。
