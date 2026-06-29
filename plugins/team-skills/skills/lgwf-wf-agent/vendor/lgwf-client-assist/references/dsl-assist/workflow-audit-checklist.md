# Workflow Audit Checklist

用于验收 LGWF workflow 目录。它检查递归业务目录结构、workflow/step 类型、可生成的 `workflow.json` runtime IR、resource refs、prompt 委派和最小可运行性。

如果 workflow 包含 prompt 文件、`exec.codex_prompt`、`subgraph.react` 的 `reason` / `act` / `observe`，或 `subgraph.agent_loop` / `AGENT_LOOP` 的 Codex slot，还要读取 `references/prompt-assist/prompt-audit-checklist.md`。

## Workflow Structure Checklist

- 根目录优先包含 `workflow.lgwf` authoring source。
- 用户 authoring package 默认不保存生成的 `workflow.json`；runtime IR 由 facade 在隐藏 snapshot 中生成。
- 根目录包含 README，说明 workflow 目标、运行方式、输入和输出。
- 新建或重写的 README、prompt、人工确认说明、运行报告模板、审核摘要等面向人阅读的文本正文默认使用中文；代码、JSON key、YAML key、DSL capability 名称、文件路径、命令、API 字段、错误码和协议字段保持原文。
- 不存在固定的 `steps/`、`workflows/` 或 `rules/` 容器目录。
- 包含 `workflow.lgwf` 的业务目录按 workflow 验收；不包含它的业务目录按普通 step 验收。
- 普通 step 只包含自己的 `agents/`、`scripts/` 等资源，不包含 `workflow.lgwf`。
- `agents/`、`scripts/`、`shared/` 等资源目录不作为业务 step 识别。
- workspace 输入和运行产物目录，例如 `data/`、`reports/`，不放入 workflow package；它们位于独立 `--work-dir`。

## Root Workflow Checklist

- 根 `workflow.lgwf` 可通过 `scripts/lgwf.py audit <package-root>\workflow.lgwf` 做 authoring 阶段机器可读检查；agent 应先读取 JSON diagnostics，修复后重复 audit。
- 根 `workflow.lgwf` 可通过 `scripts/lgwf.py compile` 编译；运行时 facade 在 `<work_dir>\.lgwf\workflow\` snapshot 中自动完成编译。
- 当前 workflow 可直接声明普通 step 对应的 `PY`、`CODEX`、`APPROVAL`、`REACT`、`AGENT_LOOP`、`PARALLEL`。
- 子 workflow 通过 `STEP ... WORKFLOW` 引用，且父 workflow 不重复声明其内部节点。
- 已有复杂 workflow 重构后，根 workflow 应只表达业务骨架；脚本、prompt、approval 和 ReAct 细节应下沉到对应阶段子 workflow。
- 单节点、人工确认和输出校验优先作为普通 step，不强制包装成子 workflow。
- 如果兼容旧 package 时同时存在 `workflow.lgwf` 和 `workflow.json`，snapshot 中的新编译结果覆盖旧 JSON。
- `PY`、`CODEX`、`APPROVAL`、`REACT`、`AGENT_LOOP`、`STEP ... WORKFLOW` 是 Authoring DSL v2 的高层声明。
- 新建 workflow 优先使用 `FLOW { ... }` 集中表达全局流程；块内 `THEN` lowering 为 `edges`，`WHEN "route_key" THEN` lowering 为 `routes`。旧 `FLOW ...;` 和独立 `ROUTE ...;` 只作为兼容写法保留。
- `READ`、`WRITE`、`RESULT`、`INSTRUCTION` 必须使用 `state.*` runtime state path。
- `PROMPT`、`SCRIPT`、`CONTEXT file|dir` 必须使用相对文件资源路径。
- `REACT` sugar 只表达 `subgraph.react`，必须包含 `REASON`、`ACT`、`OBSERVE`、`DECIDE`；slot 可使用 `CODEX`、`PY`、`TOOL` 或 `WORKFLOW`，其中 `WORKFLOW` slot 必须声明 `RESULT state.*`。
- `REACT SPEC "<path>"` 可选；配置后只约束 `REASON`、`ACT`、`OBSERVE`，冲突时以 spec 为准，不传给 `DECIDE PY`。
- `AGENT_LOOP` sugar 只表达 `subgraph.agent_loop`，必须包含 `OBSERVE`、`DIAGNOSE`、`PLAN`、`ACT`、`VERIFY`、`DECIDE`；runtime 按声明顺序执行 slot。
- `AGENT_LOOP` slot 可使用 `CODEX`、`PY`、`TOOL` 或 `WORKFLOW`；`WORKFLOW` slot 必须声明 `RESULT state.*`。`VERIFY` 结果必须包含 boolean `passed`；`DECIDE` 结果必须包含 `category` 和 `reason`，可包含 `evidence`、`stop_reason`。
- `AGENT_LOOP` 默认 `TOKEN_MAX 1000000`，默认 Codex target 授权读取 `state.targets.dirs` 和 `state.targets.files`；slot 内不得覆盖 `TARGET_DIRS` / `TARGET_FILES`。
- `AGENT_LOOP` 不依赖顶层 `SANDBOX`，每轮自动使用 sandbox；失败、blocked、retry 或验证失败轮次只归档，不 promote。
- 不使用旧 `NODE ... USE ... CONFIG`、`REACT ... MAX_STEPS ... CONFIG` 或 `WATERFALL` authoring 语法。
- 编译后的 `workflow.json` 只使用 `nodes`、`edges`、`routes`、`entry_point` 顶层字段。
- node id 唯一，`entry_point` 指向存在的 node。
- `edges` 只表达无条件连接，不写条件逻辑。
- 条件逻辑使用 `flow.*`、`subgraph.react` 的 `decide` 或 `subgraph.agent_loop` 的 `DECIDE`，不塞进 edge。
- capability 来自 `src/lgwf/capabilities/catalog.json`。
- 不新增 `subgraph.package`、顶层 `subgraphs`、`policy.loop` 或 `flow.loop_guard`。

## Workflow / Step Checklist

- 每个 workflow 的 `workflow.lgwf` 只组装其直接普通 step 和直接子 workflow。
- 普通 step 的资源由父 workflow 直接引用。
- 多个直接子级共用资源放在当前 workflow 的 `shared/`。
- workflow 引用路径相对当前 `workflow.lgwf`，必须指向 `.lgwf`，且引用链不存在循环。
- `SCRIPT`、`PROMPT`、`CONTEXT workflow` 相对当前 `workflow.lgwf`，编译后成为 package-root 相对路径。
- inventory、审计或治理脚本如果声称扫描 workflow package，必须覆盖嵌套 `workflow.lgwf`，并排除 `.git`、`.lgwf`、`__pycache__`、`ws`、`reports`、`data` 等运行或产物目录。

## Resource Reference Checklist

- `prompt_ref` / `script_ref` 作为 node config 传给 client。
- `ref_root.root` 和显式 resource `root` 只使用 `workflow` 或 `workspace`。
- 所有 resource path 都是相对路径，不使用绝对路径或 `..`。
- workflow-local prompt/script 使用 `ref_root={"root":"workflow","path":"."}` 加 path-only ref，或显式 `root:"workflow"`。
- 需要 Codex 读取的 workspace 文件或目录都放入 `context_refs`。
- README 运行命令优先使用 `--workflow-lgwf` 并明确 `--work-dir`；不得把 workflow package 根目录本身作为 work dir。
- facade 把完整 package 复制到 `<work_dir>\.lgwf\workflow\`，并只在 snapshot 中生成 `workflow.json`；用户 package 中不保留 `.lgwf-compiled-*` 或生成的 JSON。
- snapshot 复制按字节保留文件内容，排除 `.git/`、`__pycache__/`、`.lgwf-compiled-*` 和 package 内部 work dir，并拒绝 symlink、junction 或其他 reparse point。
- runtime 不读取 client workspace 中的 prompt/script 内容。
- 修改计划中的目标文件必须经过路径校验 gate：只允许目标 package 内相对路径，禁止绝对路径、盘符路径、`..`、`.lgwf/`、package 越界和 `target_dirs` 外路径。

## Prompt Integration Checklist

- `reason` 映射 Draft Prompt。
- `act` 映射 Action Prompt。
- `observe` 映射 Audit Prompt。
- 不属于 Draft、Action 或 Audit 职责的普通 `exec.codex_prompt` 映射 Normal Prompt。
- `AGENT_LOOP DIAGNOSE` / `PLAN` 映射 Draft Prompt，`ACT` 映射 Action Prompt，`OBSERVE` 映射 Audit Prompt；`VERIFY` / `DECIDE` 默认优先脚本。任一循环 slot 需要多节点编排时可使用 `WORKFLOW` 子 workflow。
- `decide` 默认是脚本或轻量节点，写入 `next=continue|exit`。
- prompt 文件验收引用 `references/prompt-assist/prompt-audit-checklist.md`。
- prompt 的 `Inputs` 与 `context_refs` 或前序节点输出对齐。

## ReAct Checklist

- `subgraph.react` 包含 `reason`、`act`、`observe`、`decide`。
- `max_steps` 明确。
- slot 使用 `WORKFLOW` 时必须声明 `RESULT state.*`，并由子 workflow 写入该 state path。
- 当 `ACT` slot 会修改文件且需要多个步骤时，优先使用 `ACT WORKFLOW` 子 workflow，并在子 workflow 中把 `validate_plan` 放在真正修改文件的节点之前。
- `observe` 输出结构化 review，例如 `passed/issues/summary`。
- `decide` 读取 review 结果并输出 `next=continue|exit`。
- 如果 `decide` 使用 `exec.run_python` 更新 state，启用 `state_updates_from_stdout=true`，脚本打印 JSON object。

## Governance Refactor Checklist

- 根 workflow 的阶段命名能表达业务骨架，不暴露过多底层节点。
- 每个子 workflow 有清晰入口、固定产物路径和最小 README 或 AGENTS 说明。
- 人工确认只出现在会改变范围、批准修改或结束验收的边界上。
- 修改前存在计划 artifact，修改后存在 review 或 audit artifact。
- 路径校验失败时 workflow 停止进入修改节点，不允许由 prompt 自行“谨慎处理”替代校验。
- `artifact_contracts.json` 声明 bootstrap inputs 和脚本写入的 workspace artifacts，避免 audit 因缺少 producer 误报，也避免只声明不实际创建运行所需文件。
- 修改 DSL、workflow 文档、facade registry 或 bundled client 后，必须运行对应的 `audit`、单元测试和 facade workflow-health；不能只依赖模型审阅。

## Agent Loop Checklist

- `subgraph.agent_loop` 包含六个必填 slot：`observe`、`diagnose`、`plan`、`act`、`verify`、`decide`。
- `slot_order` 来自 `AGENT_LOOP` block 内声明顺序，审核时确认业务顺序符合目标。
- slot 使用 `WORKFLOW` 时必须声明 `RESULT state.*`，并由子 workflow 写入该 state path。
- `artifacts_path` 指向 `.lgwf/loops/<loop_id>` 这类 work dir 下的运行产物目录，不写入 workflow package。
- `status_path` 和 `report_path` 默认可省略；显式声明时必须是 `state.*`。
- `on_max` 和 `on_error` 只使用 `block` 或 `wait_human`；需要人工接管时优先用 `wait_human`。
- `TOKEN_MAX` 是正整数；默认 `1000000`。runtime 在进入下一轮前根据 `state.run.token_usage.totals.total_tokens` 的本轮增量累计判断。
- `VERIFY` 结果必须可在其 `RESULT` state path 读到 object，且包含 boolean `passed`。
- `DECIDE` 结果必须可在其 `RESULT` state path 读到 object，且 `category` 属于 `continue`、`retry`、`wait`、`wait_human`、`finish`、`block`。
- Codex token 节点级事实位于 `state.token_usage.<node_id>`；全局 token 和用时统计位于 `state.run.token_usage` 和 `state.run.node_timings`。

## Verification Checklist

- `lgwf_dsl.cli audit` 能从根 `.lgwf` 输出 `passed=true` 的 JSON audit 结果；该命令不读取 `work_dir`、pid、session、run records 或 human approval 状态。
- 所有 Markdown/JSON/Python 文件可用 UTF-8 读取。
- 所有 prompt/script/resource 引用能在对应 root 下解析到存在文件或目录。
- `lgwf_dsl.cli compile` 能从 snapshot 根 `.lgwf` 生成 `workflow.json`。
- `compile_dsl(...)` 能编译 snapshot 根 `workflow.json`。
- Python 脚本至少通过 `compileall`。
- 不为 smoke test 新增 runtime 侧目录 loader。

## Review Output

验收输出建议使用结构化摘要：

```json
{
  "passed": true,
  "issues": [],
  "summary": "简短验收摘要"
}
```

`issues` 应说明问题位置、违反的 checklist 项和建议修复方向。
