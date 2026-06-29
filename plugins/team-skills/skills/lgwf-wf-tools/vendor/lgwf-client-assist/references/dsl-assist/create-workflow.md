# 创建 Workflow

创建新的 workflow 目录或调整已有 workflow 目录时使用。

如果 workflow 包含 prompt 文件、`exec.codex_prompt` 节点、`subgraph.react` 的 `reason` / `act` / `observe` slot，或 `subgraph.agent_loop` / `AGENT_LOOP` 的 Codex slot，读取 `references/prompt-assist/guide.md`：先判断 prompt 类型，再读取对应 reference。

- Draft Prompt：`references/prompt-assist/draft-prompt.md`
- Action Prompt：`references/prompt-assist/action-prompt.md`
- Audit Prompt：`references/prompt-assist/audit-prompt.md`
- Normal Prompt：`references/prompt-assist/normal-prompt.md`
- 共享规则：`references/prompt-assist/shared-rules.md`

## 语言约束

- 新建或重写 README、prompt、人工确认说明、运行报告模板、审核摘要等面向人阅读的文本正文时，默认使用中文。
- 修改已有文件时，保持该文件已经确立的语言风格；如果文件中已有中英文混排，只调整本次新增或重写部分。
- 代码、JSON key、YAML key、DSL capability 名称、文件路径、命令、API 字段、错误码和协议字段不翻译。

## 目录风格

按业务职责递归组织目录，不增加固定的 `steps/`、`workflows/` 或 `rules/` 容器。目录类型只由 workflow source 判定：

- 包含 `workflow.lgwf` 的业务目录是 workflow 或子 workflow。
- 不包含 `workflow.lgwf` 的业务目录是普通 step。
- `agents/`、`scripts/`、`shared/` 是 package 资源目录，不判定为 step。
- `data/`、`reports/` 等 workspace 输入和运行产物目录位于独立 `--work-dir`，不放入 workflow package。
- 数字前缀只表达业务顺序，不参与目录类型判断。

```text
some_workflow/
  workflow.lgwf
  README.md
  01_generate_plan/
    agents/
      planner/
        prompt.md
  02_generate_acceptance/
    agents/
      acceptance/
        prompt.md
  03_confirm_plan_and_acceptance/
    agents/
      reviewer/
        prompt.md
  04_execute_react_loop/
    01_reason/
      agents/
        reasoner/
          prompt.md
    02_act/
      agents/
        actor/
          prompt.md
    03_observe/
      agents/
        observer/
          prompt.md
    scripts/
      decide.py
  tests/
    test_workflow_contract.py
  shared/
```

默认按 `lgwf-plan` 风格组织为根 workflow 直接组装普通 step：`01_generate_plan/` 生成计划，`02_generate_acceptance/` 生成验收标准，`03_confirm_plan_and_acceptance/` 做人工或模型确认，`04_execute_react_loop/` 执行迭代循环。`scripts/` 和 `tests/` 可以作为 workflow package 级资源目录；只有某个阶段需要独立拓扑、复用或嵌套编排时，才在该业务目录内增加自己的 `workflow.lgwf` 并由父 workflow 用 `STEP <id> WORKFLOW "<path>";` 引用。

每个 workflow 目录的 `workflow.lgwf` 负责组装其直接普通 step 和直接子 workflow。普通 step 的 agent/script 由父 workflow 直接引用；子 workflow 使用 `STEP <id> WORKFLOW "<path>";` 引用。compiler 递归嵌入完整 JSON IR，runtime 不读取源文件路径。用户 authoring package 默认不保存 `workflow.json`，它只作为 snapshot 中的 compiled runtime IR。

### Workflow 组装边界

- 当前 workflow 可以直接声明其普通 step 对应的 `PY`、`CODEX`、`APPROVAL`、`REACT`、`AGENT_LOOP`、`PARALLEL` 节点。
- 多个 ReAct Codex slot 共用稳定业务规则时，在 `REACT` 中声明可选 `SPEC "<path>"`；它约束 `REASON`、`ACT`、`OBSERVE`，不传给 `DECIDE PY`。
- 工程化长程循环使用 `AGENT_LOOP`，按声明顺序执行六个必填 slot：`OBSERVE`、`DIAGNOSE`、`PLAN`、`ACT`、`VERIFY`、`DECIDE`。循环 slot 可使用 `CODEX`、`PY`、`TOOL` 或 `WORKFLOW`；`WORKFLOW` slot 必须声明 `RESULT state.*`。`CODEX` slot 使用 `PROMPT_REF`，`VERIFY` 结果必须包含 `passed: true|false`，`DECIDE` 结果必须包含 `category` 和 `reason`。
- 只有出现独立拓扑、复用或嵌套编排需求时才创建子 workflow。
- 子 workflow 的内部节点只由它自己的 `workflow.lgwf` 声明；父 workflow 不复制这些节点。
- 子 workflow 的内部确认闭环不泄露给父 workflow；父 workflow 不承接子 workflow 的 `approve` / `revise` / `reject` route。
- 子 workflow 内部遇到用户拒绝、取消或不可继续的全局终止语义时，使用 `WHEN "reject" THEN FAIL_ALL`，而不是把 `reject` route 接到父 workflow 的汇总节点。
- 多个直接子级共用的资源放在当前 workflow 的 `shared/`；单个 step 独占资源放在该业务 step 目录。
- workflow 引用和 workflow-local resource 路径相对当前 `workflow.lgwf` 所在目录。
- 禁止绝对路径、`..`、package 越界和 workflow 引用循环。

## Step 规范

- 普通 step 不包含 `workflow.lgwf`，只保存本步骤的 `agents/`、`scripts/` 等资源。
- 普通 step 的执行节点在父 workflow 的 `workflow.lgwf` 中声明和串联。
- 子 workflow 可以包含多个普通 step，也可以继续引用更深层子 workflow。
- 一个只有单脚本、单 prompt、人工确认或输出校验的业务动作通常是普通 step，不为形式统一额外创建 workflow。

## DSL 规则

workflow 可以同时组装普通 step 和子 workflow：

```text
WORKFLOW lgwf_plan_style;
ENTRY generate_plan;

DEFAULTS {
  ref_root workflow ".";
  timeout_seconds 900;
  instruction_path "{node}_instruction";
  result_path "{node}_result";
}

CODEX generate_plan
  PROMPT "01_generate_plan/agents/planner/prompt.md"
  RESULT state.plan;

CODEX generate_acceptance
  PROMPT "02_generate_acceptance/agents/acceptance/prompt.md"
  RESULT state.acceptance;

APPROVAL confirm_plan_and_acceptance
  PROMPT "请确认 plan 与 acceptance 是否可执行。"
  VALUE state.confirmation;

REACT execute_react_loop {
  REASON CODEX reason
    PROMPT_REF "04_execute_react_loop/01_reason/agents/reasoner/prompt.md"
    RESULT state.react.reason;
  ACT CODEX act
    PROMPT_REF "04_execute_react_loop/02_act/agents/actor/prompt.md"
    RESULT state.react.act;
  OBSERVE CODEX observe
    PROMPT_REF "04_execute_react_loop/03_observe/agents/observer/prompt.md"
    RESULT state.react.observe;
  DECIDE PY decide
    SCRIPT "04_execute_react_loop/scripts/decide.py"
    RESULT state.react.decision;
}

FLOW {
  generate_plan THEN generate_acceptance THEN confirm_plan_and_acceptance THEN execute_react_loop;
}
```

推荐用 `FLOW { ... }` 集中描述完整流程；块内 `a THEN b THEN c` 表达无条件顺序边，`a WHEN "route_key" THEN b` 表达 route key 到目标节点的跳转。`THEN FAIL_ALL` 是保留控制流目标，用于失败终止当前 workflow 并向父 workflow 传播；不要创建名为 `FAIL_ALL` 的节点。旧的单条 `FLOW a THEN b;` 和独立 `ROUTE a WHEN ...;` 仍兼容，但新建 workflow 优先使用块语法，避免跳转逻辑和整体流程分离。

子 workflow 内部的人工确认或修订循环应自洽表达，父 workflow 只串联阶段：

```text
FLOW {
  confirm_design
    WHEN "approve" THEN apply_design
    WHEN "revise" THEN revise_design
    WHEN "reject" THEN FAIL_ALL;

  revise_design
    WHEN "approve" THEN apply_design
    WHEN "revise" THEN revise_design
    WHEN "reject" THEN FAIL_ALL;

  apply_design THEN scaffold_package;
}
```

这样父 workflow 不需要出现 `__route__<child>`、`reject` 汇总分支或子流程内部节点名。

`workflow.json` 是 runtime IR，但用户 authoring package 默认不保存该文件。通过 `scripts/lgwf.py run` 运行时，client 先把 package 复制到 `<work_dir>\.lgwf\workflow\`，再在 snapshot 中生成 runtime IR。`workflow.json` 仍只使用 `src/lgwf/compiler/dsl_schema.json` 接受的字段：

```json
{
  "nodes": [],
  "edges": [],
  "routes": [],
  "entry_point": "node_id"
}
```

从 `src/lgwf/capabilities/catalog.json` 选择 runtime capability。不要靠猜测新增 DSL 字段。Authoring DSL v2 使用 `PY`、`CODEX`、`APPROVAL`、`REACT`、`AGENT_LOOP` 高层声明 lowering 到现有 runtime JSON IR；不新增业务专属 mapper。

`CODEX` 小型结构化结果可用 `OUTPUT_JSON "path.json"`；大 JSON 使用 `OUTPUT_JSON "path.json" AS_FILE`，由 Codex 写文件，LGWF runner 验证文件存在、UTF-8、JSON 可解析且顶层是 object。

`APPROVAL` 已足够表达人工确认节点。不要在 `.lgwf` 或 `workflow.json` 中写入 Agent Host、`main_agent`、`session_id`、controller payload、approval worker/window 或 CLI 调用；这些属于 `lgwf_client.main_agent` 控制面和执行 agent loop。

## 资源引用

在 node config 中使用 `ref_root` 和 resource refs。新的 workflow 目录只应使用两个 root：

- `workflow`：当前 workflow 目录根目录。
- `workspace`：用户项目/workspace 根目录。

workflow 通过 `scripts/lgwf.py run --work-dir <dir>` 指定用户 workspace root。workflow package 与 work dir 不能是同一目录；work dir 位于 package 内部时，snapshot 复制会排除整个 work dir。不要把运行生成的 `data/`、`reports/`、`.lgwf/` 或其他 workspace artifact 写回 workflow package，也不要在 `workflow.json` 中写入本地 workspace 绝对路径。

```json
{
  "ref_root": {"root": "workflow", "path": "."},
  "prompt_ref": {
    "path": "02_do_plan/01_draft/agents/designer/prompt.md"
  },
  "context_refs": [
    {"root": "workspace", "path": "data/input.json", "type": "file"}
  ]
}
```

规则：

- `ref_root.root` 和显式 resource `root` 必须是 `workflow` 或 `workspace`。
- path 相对于选定 root。
- 不允许绝对路径。
- 不允许 `..`。
- runtime 不读取该文件。
- client runner 在本机解析并读取。
- 对于 `exec.codex_prompt`，prompt 期望 Codex 读取的每个 workspace 文件或目录都要放入 `context_refs`。
- 对于 Codex 真正要分析的用户授权目标目录或文件，使用 `target_dirs` / `target_files`，或 Authoring DSL 的 `TARGET_DIR` / `TARGET_FILE` / `TARGET_DIRS state.*` / `TARGET_FILES state.*`；不要把动态分析目标塞进 `context_refs`。
- `target_dirs` / `target_files` 可使用绝对路径，由 client runner 校验存在性和文件/目录类型；它们不是 workflow resource refs。
- 生成 prompt 文件时，不在本文件展开 prompt 规则；读取 `references/prompt-assist/guide.md`，并保持 prompt 的 `Inputs` 与 `context_refs` 对齐。
- 省略 `cwd`，让执行默认发生在 workspace root；legacy `cwd` 只用于旧 workflow 兼容。

## 常用 Capability

- `exec.run_shell`：在 client 上运行 shell command。
- `exec.run_python`：在 client 上运行 inline Python 或 script reference。
- `exec.codex_prompt`：使用内联 prompt 或 `prompt_ref` 运行 Codex。
- `flow.if`、`flow.switch`、`flow.guard`、`flow.assign`：控制 state 和 routing。
- `subgraph.react`：固定 reason / act / observe / decide loop。
- `subgraph.agent_loop`：工程化 Agent Loop，包含显式状态、每轮 sandbox、验证、决策、归档、报告、`TOKEN_MAX` 和人工接管控制策略；authoring 时使用 `AGENT_LOOP`。
- `subgraph.workflow`：执行 compiler 嵌入的完整 workflow JSON IR；authoring 时使用 `STEP ... WORKFLOW`。

`subgraph.react` 和 `subgraph.agent_loop` 中的 prompt 设计职责由 `references/prompt-assist/guide.md` 处理：`reason` / `diagnose` / `plan` 使用 Draft Prompt，`act` 使用 Action Prompt，`observe` 使用 Audit Prompt，`decide` 默认优先脚本或轻量节点。不属于 Draft、Action 或 Audit 职责的普通 `exec.codex_prompt` 使用 Normal Prompt。

`AGENT_LOOP` 默认向内部 Codex slot 注入 `target_dirs_path="targets.dirs"` 和 `target_files_path="targets.files"`，slot 内不要声明 `TARGET_DIRS` / `TARGET_FILES` 覆盖。运行时 `exec.codex_prompt` 会写节点级 `state.token_usage.<node_id>`；全局累计和用时由 runtime metrics 写入 `state.run.token_usage` 和 `state.run.node_timings`。`TOKEN_MAX` 默认 `1000000`，在准备进入下一轮之前判断，达到预算后进入 `waiting_human`。

除非任务明确要求架构工作，否则不要新增 `flow.join`、parallel fan-in 或新的 DSL schema 字段。

对于 ReAct decide slot，如果脚本需要写入 `next=continue` 或 `next=exit`，优先使用带 `state_updates_from_stdout=true` 的 `exec.run_python`。脚本必须打印一个 JSON object，其中 key 是 runtime state path。

## 最小检查

创建 workflow 后运行：

```powershell
python <skill-dir>\scripts\lgwf.py audit <package-root>\workflow.lgwf
.venv\Scripts\python.exe -m unittest discover -s test -p "test_*.py"
.venv\Scripts\python.exe -m compileall -q src test
```

如需 workflow 专属编译和运行检查，先运行 `scripts/lgwf.py audit <package-root>\workflow.lgwf` 修复 authoring diagnostics，再使用 `scripts/lgwf.py run --workflow-lgwf`。facade 会在 `<work_dir>\.lgwf\workflow\` snapshot 中再次 audit、compile 和运行，确保 runtime `workflow` root 与复制后的资源路径一致，同时不污染用户 package。
