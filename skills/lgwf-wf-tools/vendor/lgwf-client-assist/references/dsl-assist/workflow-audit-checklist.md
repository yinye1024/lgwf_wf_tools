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
- 当前 workflow 可直接声明普通 step 对应的 `PY`、`CODEX`、`APPROVAL`、`REVIEW`、`REACT`、`AGENT_LOOP`、`PARALLEL`。
- 子 workflow 通过 `STEP ... WORKFLOW` 引用，且父 workflow 不重复声明其内部节点。
- 子 workflow 的 `approve` / `revise` / `reject` 等交互细节不得泄露到父 workflow；拒绝、取消或不可继续时，子 workflow 内部 route 到保留目标 `FAIL_ALL`。
- 单节点、人工确认和输出校验优先作为普通 step，不强制包装成子 workflow。
- `PY`、`CODEX`、`APPROVAL`、`REVIEW`、`HANDOFF_FILES`、`REACT`、`AGENT_LOOP`、`STEP ... WORKFLOW` 是 Authoring DSL v2 的高层声明。
- `APPROVAL` route key 只能是 `approve` / `reject`；如果出现 `revise`、`minor_change` 等非二元 route，audit 应失败，并提示改用固定三选项的 `REVIEW`。
- `REVIEW` 固定用于 `approve` / `revise` / `reject` 三个评审分支，不允许自定义 options；audit 应检查显式 route 覆盖三分支，`reject` 通常指向 `FAIL_ALL`，`revise` 回到当前 `REVIEW` 或修订节点后回到当前 `REVIEW`，apply/finalize 只从 `approve` 到达。
- `REVIEW CONTEXT state.*` 必须是业务 JSON object，不应是 `RESULT`、`decision`、`approval`、`review_result` 等 control-plane state；`REVIEW RESULT` 和 `PERSIST` 只能作为控制面审计记录，不能作为 confirmed/final/proposal 等业务 artifact 来源。
- 新建 workflow 优先使用 `ENTRY FLOW main` 声明 authoring 层入口，并用命名 `FLOW main START ... THEN ...` 表达全局流程；命名 flow 不需要 `{}`，编译后入口解析到 `START` 节点。
- 多分支使用独立 `ROUTE <node>` 或 `ROUTE <node> READ state.*`；人机多选使用 `CHOICE ... OPTION key LABEL "..." THEN target`。
- `FAIL_ALL` 只能作为 route target 使用，不允许作为 node id；命中后当前 workflow failed，并向父 workflow 传播失败，父 workflow 后续 step 不应运行。
- `READ`、`WRITE`、`RESULT` 必须使用 `state.*` runtime state path；`INSTRUCTION` 不是 authoring DSL 字段，instruction trace path 由 compiler 自动生成。
- `PROMPT`、`SCRIPT`、`CONTEXT file|dir` 必须使用相对文件资源路径。
- `REACT` sugar 只表达 `subgraph.react`，必须包含 `REASON`、`ACT`、`OBSERVE`、`DECIDE`；slot 可使用 `CODEX`、`PY`、`TOOL` 或 `WORKFLOW`，其中 `WORKFLOW` slot 必须声明 `RESULT state.*`。
- `REACT SPEC "<path>"` 可选；配置后只约束 `REASON`、`ACT`、`OBSERVE`，冲突时以 spec 为准，不传给 `DECIDE PY`。
- `AGENT_LOOP` sugar 只表达 `subgraph.agent_loop`，必须包含 `OBSERVE`、`DIAGNOSE`、`PLAN`、`ACT`、`VERIFY`、`DECIDE`；runtime 按声明顺序执行 slot。
- `AGENT_LOOP` slot 可使用 `CODEX`、`PY`、`TOOL` 或 `WORKFLOW`；`WORKFLOW` slot 必须声明 `RESULT state.*`。`VERIFY` 结果必须包含 boolean `passed`；`DECIDE` 结果必须包含 `category` 和 `reason`，可包含 `evidence`、`stop_reason`。
- `AGENT_LOOP` 默认 `TOKEN_MAX 1000000`，默认 Codex target 授权读取 `state.targets.dirs` 和 `state.targets.files`；slot 内不得覆盖 `TARGET_DIRS` / `TARGET_FILES`。
- `AGENT_LOOP` 不依赖顶层 `SANDBOX`，每轮自动使用 sandbox；失败、blocked、retry 或验证失败轮次只归档，不 promote。
- `RUN_WORKFLOW + PY map_*` 用于串联独立 workflow package；mapper 只做 state shape adapter，不默认复制文件。
- 有可审计文件副作用的 `PY` 必须声明 `CONTRACT`；`CONTRACT` 不用于声明 stdout state patch。
- `RESULT state.*`、`UPDATES_STATE { WRITE state.*; }` 和 `CONTRACT WRITE state.*` 分别服务执行结果、stdout state patch 和业务契约边界；三者是独立系统，可以声明同一个 state path。
- `PY` 需要让 workflow 上可见 stdout state patch 写入范围时，使用 `UPDATES_STATE { WRITE state.*; }` 覆盖脚本 stdout 会写入的最终 state path；裸 `UPDATES_STATE` 保持兼容模式，不检查具体 path。
- `PY SCRIPT` 读取 `.lgwf/`、`reports/` 或 `data/` 下的业务 artifact 时，必须声明 `CONTRACT READ workspace file "..."`。audit 会扫描 `Path("...").read_text(...)`、`Path("...").read_bytes(...)`、`open("...", "r")`、`open("...")`、`load_json(root / ".lgwf" / "file.json")` 和 `read_json(...)`；缺少 contract 时应报 `LGWF_PY_FILE_READ_CONTRACT_MISSING`，读取路径未声明时应报 `LGWF_PY_FILE_READ_CONTRACT_MISMATCH`。
- `PY SCRIPT` 写入 `.lgwf/`、`reports/` 或 `data/` 下的业务 artifact 时，也必须声明 `CONTRACT WRITE workspace file "..."`。audit 会扫描 `Path("...").write_text(...)`、`Path("...").write_bytes(...)`、`open("...", "w|a|x", ...)` 和 `write_json(lgwf_dir / "out.json", payload)`；缺少 contract 时应报 `LGWF_PY_FILE_WRITE_CONTRACT_MISSING`，写出路径未声明时应报 `LGWF_PY_FILE_WRITE_CONTRACT_MISMATCH`。
- `PY CONTRACT READ` 在脚本执行前校验，`PY CONTRACT WRITE` 在 `RESULT` 和 `UPDATES_STATE` 应用后的最终 state 上校验；修复 audit 报错时不要只补说明文字，必须让 contract 与脚本真实输入输出一致。
- `RUN_WORKFLOW WORKFLOW` 和 `WORK_DIR` 使用相对路径，不使用绝对路径或 `..`；运行时默认创建轻量隔离 `workspace/work_dir`，`WORK_DIR` 只作为 `declared_work_dir` 记录。
- `RUN_WORKFLOW RESULT` 应被后续 `PY map_*`、汇总节点或下游 workflow 消费；`RUN_WORKFLOW INPUT` 应来自初始 input 或上游 mapper writer。
- 需要从上游 child 交接业务文件或目录时，优先使用 `HANDOFF_FILES`。`FROM` 指向上游 `RUN_WORKFLOW RESULT`；`COPY_FILE` / `COPY_DIR` 源路径相对上游实际 `work_dir`；`AS` 目标路径相对父 `<work_dir>/.lgwf/handoff/<node_id>/`；`RESULT` 字段值是复制后文件或目录的绝对路径，供下游隔离 child 读取；结果同时包含 `handoff_files` 对象，适合下游 `PY INPUT state.handoff_files`；目录交接默认整体替换目标目录。
- `.lgwf/child-runs/*.json` 只用于诊断和状态展示，不作为常规业务数据通道；record 中的实际 child `work_dir` 位于 `.lgwf/isolations/run_workflow/<node_id>/work_dir`，child 人工确认由父 status 透传为 `child_human_approval`。
- workflow 拓扑只使用当前 Authoring DSL v2 声明和 `STEP ... WORKFLOW` 组合；不要新增未在 schema/catalog 中定义的 authoring 结构。
- 编译后的 `workflow.json` 只使用 `nodes`、`edges`、`routes`、`entry_point` 顶层字段。
- node id 唯一，`entry_point` 指向存在的 node。
- `edges` 只表达无条件连接，不写条件逻辑。
- 条件逻辑使用 `flow.*`、`subgraph.react` 的 `decide` 或 `subgraph.agent_loop` 的 `DECIDE`，不塞进 edge。
- capability 来自 `src/lgwf/capabilities/catalog.json`。
- 不新增 `subgraph.package`、顶层 `subgraphs`、`policy.loop` 或 `flow.loop_guard`。

## Workflow / Step Checklist

- 每个 workflow 的 `workflow.lgwf` 只组装其直接普通 step 和直接子 workflow。
- 普通 step 的资源由父 workflow 直接引用。
- 父 workflow 只表达阶段编排，不写子 workflow 内部确认分支；检查是否存在把子 workflow 的 `reject` route 接到父级汇总节点的耦合写法，必要时改为子 workflow 内部 `THEN FAIL_ALL`。
- 多个直接子级共用资源放在当前 workflow 的 `shared/`。
- workflow 引用路径相对当前 `workflow.lgwf`，必须指向 `workflow.lgwf`，且引用链不存在循环。
- `SCRIPT`、`PROMPT`、`CONTEXT workflow` 相对当前 `workflow.lgwf`，编译后成为 package-root 相对路径。

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
- `observe` 输出结构化 review，例如 `passed/issues/summary`。
- `decide` 读取 review 结果并输出 `next=continue|exit`。
- 如果 `decide` 使用 `exec.run_python` 更新 state，新 workflow 优先使用 `UPDATES_STATE { WRITE state.*; }` 显式声明 stdout patch 写入范围；脚本打印 JSON object，key 是 runtime state path。裸 `UPDATES_STATE` 仅作兼容模式。

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
