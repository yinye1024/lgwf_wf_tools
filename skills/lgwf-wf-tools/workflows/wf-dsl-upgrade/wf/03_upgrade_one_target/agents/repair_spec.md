# 单目标 DSL 修复规则

当前 ReAct loop 只服务一个 `.lgwf` 文件，也就是当前 FOREACH item。运行时只应依赖 `state.wf_dsl_upgrade.current_target`、`state.wf_dsl_upgrade.current_audit` 和 `TARGET_FILES` 暴露的当前文件。

必须遵守：

- 只读取和修改 `state.wf_dsl_upgrade.current_target.path` 指向的文件；该文件必须同时来自 `current_target` 和 `TARGET_FILES`。
- 不得修改 `state.wf_dsl_upgrade.target_files` 之外的文件，不得扫描或改写同目录其他 workflow。
- 根据 `state.wf_dsl_upgrade.current_audit.diagnostics` 做最小修复。
- 优先补齐缺失 `CONTRACT`、修正 DSL 语法和声明位置，不改变业务意图、节点顺序、节点 id、脚本引用或 prompt 引用。
- 补 `CONTRACT` 时只声明可从当前文件和 diagnostics 证实的 state/workspace 边界；没有业务 I/O 的节点写 `CONTRACT {}`，不要猜测隐藏依赖。
- `dry_run` 正常不会进入写入式修复；如果上下文显示 mode 为 `dry_run`，只输出分析，不写文件。
- 不得改写运行态 `.lgwf/`、`ws/`、`reports/` 下的任何文件，也不得生成临时文件或报告。
- 如果 diagnostics 缺少足够语义上下文，保留现状，由 `finalize_target` 标记 `needs_manual_review`。
