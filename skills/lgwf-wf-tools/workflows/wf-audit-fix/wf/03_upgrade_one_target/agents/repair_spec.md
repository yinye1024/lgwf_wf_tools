# 单目标 DSL 修复闭环规则

当前 ReAct loop 只处理当前 FOREACH item 指向的一个 `.lgwf` 文件。`prepare_repair_context` 已把授权边界写入 `current_target`、`TARGET_FILES` 和 `.lgwf/current_target_context.json`；`audit_current_target` 已完成第 0 次 audit check，并把 diagnostics 写入 `state.wf_audit_fix.current_audit`。

必须遵守：

- 只读取和修改 `state.wf_audit_fix.current_target.path` 指向的文件；该文件必须同时来自 `current_target` 和 `TARGET_FILES`。
- 不得修改 `state.wf_audit_fix.target_files` 之外的文件，不得扫描或改写同目录其他 workflow。
- `dry_run` 不进入写入式修复；如果上下文显示 mode 为 `dry_run`，只输出分析，不写文件。
- 不得改写运行态 `.lgwf/`、`ws/`、`reports/` 下的任何文件，也不得生成临时文件或报告。
- `REASON` 必须根据当前 audit check 的 diagnostics 逐条给出修正方案，并读取上一轮 `repair_observation` / `repair_decision` 判断是否出现无进展、诊断变化或局部改善。
- `ACT` 必须执行 reason 的修正方案，并且每处改动都对应当前 diagnostics。
- `OBSERVE PY` 会运行 `scripts/observe_repair.py` 复跑 audit check，写回 `.lgwf/current_target_audit.json` 和 `.lgwf/repair_observation.json`。
- `DECIDE PY` 会把 observe 结果归纳为 `repair_decision`；下一轮 `REASON` 必须消费该反馈，不能重复上一轮已证明无效的修法。
- `LGWF_CONTRACT_REQUIRED_MISSING` 是机械可修复诊断：为对应节点补齐 `CONTRACT`；没有跨节点 state/workspace I/O 的节点写 `CONTRACT {}`。
- 补 `CONTRACT` 时只声明当前文件和 diagnostics 能证实的 state/workspace 边界，不改变业务意图、节点顺序、节点 id、脚本引用或 prompt 引用。
