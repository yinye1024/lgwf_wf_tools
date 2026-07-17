# lgwf-wf-convert

`lgwf-wf-convert` 用于把现有 prompt workflow 目录转换为 `wf-create-fast` 可消费的完整 target file。它是 `lgwf-wf-tools` 的内部 workflow package。

## 当前范围

- 收集待转换 prompt workflow 的目标目录和输出目标。
- 索引 prompt、agent、resource、README、workflow 说明等文本文件。
- 使用 ReAct 分析源 prompt workflow 的结构、职责、业务契约和缺口。
- 区分必须迁移的业务逻辑与不迁移的 prompt 执行技巧，例如执行矩阵、预填充、few-shot、角色强化和格式诱导。
- 使用 ReAct 生成 `wf-create-fast` 创建输入 proposal、`conversion_mapping` 和 `parity_requirements`。
- 人工确认 proposal 后固化为 `.lgwf/wf_create_fast_input.json`。
- 写入 `.lgwf/wf_create_fast_handoff.json` 作为完整 handoff target file。
- HANDOFF 给主 agent，由主 agent 把该 handoff target file 作为 `wf-create-fast` 的 `request.target_file` 启动后续创建流程。

## 不做的事

- 不在 `wf-convert` 内直接完成最终目标 LGWF workflow 实现；最终实现由 `wf-create-fast` 的 handoff 交给主 agent。
- 不在 `wf-convert` 内直接启动 `wf-create-fast`，也不生成转换报告或业务一致性报告；`wf-convert` 只负责把已确认的转换输入 handoff 给主 agent。
- 不跳过 `wf-create-fast` 的需求、业务流、scaffold 和 handoff 边界。
- 不自动调用创建实现链路、`wf-prompt-fix`、`wf-prompt-upgrade`、`wf-fix` 或其他下游 workflow。
- 不保证源 workflow 业务 happy path 成功。

## 运行状态

运行状态只写入 `ws/.lgwf`。目标 package 根目录不得写入 `.lgwf`。

## ReAct 目录

业务流确认阶段的两个 ReAct 使用独立目录，私有 prompt、Decide 和 Observe 子流程不得交叉引用：

```text
wf/04_confirm_business_flow/
  inspect_prompt_workflow_react/
    agents/spec.md
    agents/reason.md
    agents/act.md
    agents/observe.md
    scripts/decide.py
    scripts/validate.py
    scripts/merge.py
    ob.lgwf
  propose_create_input_react/
    agents/spec.md
    agents/reason.md
    agents/act.md
    agents/observe.md
    scripts/decide.py
    scripts/validate.py
    scripts/merge.py
    ob.lgwf
```

`spec.md` 对应 ReAct 规格，`reason.md`、`act.md`、`observe.md` 分别对应自己的 slot；各目录的 `ob.lgwf` 只编排本 ReAct 的复合 Observe。跨 ReAct 只通过父 workflow 声明的 `.lgwf` canonical artifact 交接。

## `wf-create-fast` handoff

`.lgwf/wf_create_fast_handoff.json` 是 `wf-convert` 交给 `wf-create-fast` 的完整 target file，包含 `raw_intent`、`workflow_name`、`target_package_root`、`source_business_contract`、`conversion_mapping` 和 `prompt_workflow_context`。

主 agent 接手后创建一个小的 `wf-create-fast` 启动输入，其中 `request.target_file` 指向 `.lgwf/wf_create_fast_handoff.json`。

## ReAct 反馈闭环

`inspect_prompt_workflow_react` 和 `propose_create_input_react` 的 `observe` 都拆成三个步骤：

1. Python observer 检查 schema、固定枚举、引用、覆盖关系等确定性规则。
2. Codex observer 只检查职责边界、业务语义、迁移意图和人工可理解性，不重复 Python 检查。
3. Python merge 合并两个报告，生成唯一 canonical observe。

两个 canonical observe 分别写入 `.lgwf/prompt_workflow_inspection_observe.json` 和 `.lgwf/wf_create_fast_input_observe.json`。`inspect_prompt_workflow_react/scripts/decide.py` 与 `propose_create_input_react/scripts/decide.py` 只允许读取 canonical observe；文件缺失、schema 非法、阶段不匹配或结论冲突时一律 fail closed，继续下一轮 ReAct。

canonical observe 中每个 issue 都包含 `blocking`：

- `blocking=true`：当前产物不能进入下一阶段，Decide 继续下一轮 ReAct。
- `blocking=false`：允许流程继续，但反馈不能丢失。inspection 的非阻塞 issue 会进入 proposal 的 `reason`；proposal 的非阻塞 issue 会写入 `.lgwf/wf_create_fast_input_confirmation_context.json`，由人工确认处理。

下一轮 `reason` 同时读取当前业务产物和上一轮 canonical observe，必须生成 `issue_resolution_plan`；`act` 按该计划最小修复，避免无关重写。第一轮由 `index_prompt_files.py` 创建带 `verdict=initial` 的 canonical observe 占位文件和空业务产物，确保 context 文件存在。
