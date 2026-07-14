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

- 当前 workflow 可以直接声明其普通 step 对应的 `PY`、`CODEX`、`APPROVAL`、`REVIEW`、`REACT`、`AGENT_LOOP`、`PARALLEL` 节点。
- 多个 ReAct Codex slot 共用稳定业务规则时，在 `REACT` 中声明可选 `SPEC "<path>"`；它约束 `REASON`、`ACT`、`OBSERVE`，不传给 `DECIDE PY`。
- 多轮 `REACT` 中，`OBSERVE` / `DECIDE` 如果通过 contract 写出 observation、diagnostics、decision 或反馈文件，下一轮 `REASON` 必须通过 `CONTRACT READ` 或 workspace file context 读取这些反馈；`state.next` 只作为路由控制，不要求给 `REASON` 消费。
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
ENTRY FLOW main;

DEFAULTS {
  ref_root workflow ".";
  timeout_seconds 900;
  result_path "{node}_result";
}

CODEX generate_plan
  PROMPT "01_generate_plan/agents/planner/prompt.md"
  RESULT state.plan;

CODEX generate_acceptance
  PROMPT "02_generate_acceptance/agents/acceptance/prompt.md"
  RESULT state.acceptance;

REVIEW confirm_plan_and_acceptance
  CONTEXT state.plan
  PROMPT "03_confirm_plan_and_acceptance/review.md"
  RESULT state.confirmation;

REACT execute_react_loop MAX 3
  REASON CODEX
    PROMPT_REF "04_execute_react_loop/01_reason/agents/reasoner/prompt.md"
    RESULT state.react.reason
  ACT CODEX
    PROMPT_REF "04_execute_react_loop/02_act/agents/actor/prompt.md"
    RESULT state.react.act
  OBSERVE CODEX
    PROMPT_REF "04_execute_react_loop/03_observe/agents/observer/prompt.md"
    RESULT state.react.observe
  DECIDE PY
    SCRIPT "04_execute_react_loop/scripts/decide.py"
    RESULT state.react.decision;

FLOW main
  START generate_plan
  THEN generate_acceptance
  THEN confirm_plan_and_acceptance
  THEN execute_react_loop;
```

推荐用 `ENTRY FLOW main` 声明 authoring 层入口，用命名 `FLOW main START ... THEN ...` 表达主流程。命名 flow 不需要 `{}`；`FLOW` 本身不是 runtime node，编译后入口会解析到 `START` 节点。`THEN FAIL_ALL` 是保留控制流目标，用于失败终止当前 workflow 并向父 workflow 传播；不要创建名为 `FAIL_ALL` 的节点。

子 workflow 内部的人工确认或修订循环应自洽表达，父 workflow 只串联阶段：

```text
ROUTE confirm_design
  WHEN "approve" THEN apply_design
  WHEN "revise" THEN revise_design
  WHEN "reject" THEN FAIL_ALL;

ROUTE revise_design
  WHEN "approve" THEN apply_design
  WHEN "revise" THEN revise_design
  WHEN "reject" THEN FAIL_ALL;

FLOW apply_design
  THEN scaffold_package;
```

这样父 workflow 不需要出现 `__route__<child>`、`reject` 汇总分支或子流程内部节点名。

### 独立 workflow 串联

当父 workflow 需要调度已有的独立 workflow package，而不是把子 workflow 在编译期嵌入当前包时，使用 `RUN_WORKFLOW`。父 workflow 只负责规划顺序、准备输入、等待 child 完成和收集结果；运行时会默认为 child 创建轻量隔离 `workspace` 和 `work_dir`，避免不同 run 或并发 child 串 `.lgwf` 状态。`WORK_DIR` 仍必须声明安全相对路径，但只作为 `declared_work_dir` 记录，不作为实际 child 运行目录。

```text
RUN_WORKFLOW prompt_fix
  WORKFLOW "workflows/wf-prompt-fix/wf/workflow.lgwf"
  WORK_DIR "workflows/wf-prompt-fix/ws"
  INPUT state.pipeline.target
  RESULT state.pipeline.prompt_fix_result;

PY map_prompt_upgrade_input
  SCRIPT "scripts/map_prompt_upgrade_input.py"
  INPUT state.pipeline.prompt_fix_result
  RESULT state.pipeline.prompt_upgrade_input
  UPDATES_STATE {
    WRITE state.pipeline.prompt_upgrade_input;
  };

RUN_WORKFLOW prompt_upgrade
  WORKFLOW "workflows/wf-prompt-upgrade/wf/workflow.lgwf"
  WORK_DIR "workflows/wf-prompt-upgrade/ws"
  INPUT state.pipeline.prompt_upgrade_input
  RESULT state.pipeline.prompt_upgrade_result;

FLOW prompt_fix THEN map_prompt_upgrade_input THEN prompt_upgrade;
```

`PY map_*` 是业务输入适配器，不是 runtime 内置 mapper，也不默认做文件拷贝。它读取上一个 child result，把字段整理成下一个 child workflow 的 input shape；只有下游 workflow 明确要求固定文件位置时，mapper 才可以额外复制文件。推荐 mapper 从 stdin 读取 `INPUT state.*` 对应的 JSON object，并用 stdout 输出 state path updates；新 workflow 优先使用 `UPDATES_STATE { WRITE state.*; }` 显式列出 stdout 会写入的 state path：

```python
import json
import sys

prompt_fix_result = json.load(sys.stdin)
payload = {
    "target": prompt_fix_result["final_state"]["target"],
    "fix_report": prompt_fix_result.get("latest_run", {}).get("change_summary", {}),
}

print(json.dumps({"pipeline.prompt_upgrade_input": payload}, ensure_ascii=False))
```

不要把 `.lgwf/child-runs/*.json` 作为常规业务数据通道；它是父 workflow 的 child 运行摘要，适合诊断和状态展示。`RUN_WORKFLOW` 中 child 的人工确认会通过父 workflow status 暴露为 `pending_action.type="child_human_approval"`，父侧 approval 提交后继续等待 child 完成。

`RUN_WORKFLOW + PY map_*` 串联会在 authoring audit 中做基础 handoff check：`WORKFLOW` 和 `WORK_DIR` 必须是安全相对路径，child `workflow.lgwf` 会递归 audit，重复 `WORK_DIR`、未被消费的 child result、缺少上游 writer 的 child input 会作为 error diagnostics 返回。mapper 是 state shape adapter，不默认复制文件；复杂 mapper 仍可把 `target_dir`、`report_path`、`artifact_paths` 等字段写入下游 payload。如果只需要从上游 child 交接业务文件或目录，优先使用 `HANDOFF_FILES`，不要手写拷贝脚本。不要直接读取 `.lgwf/child-runs/*.json` 作为下游数据来源。

`RUN_WORKFLOW` 的实际 child 运行目录位于父 `<work_dir>/.lgwf/isolations/run_workflow/<node_id>/work_dir`，隔离 workspace 位于同级 `workspace`。child run record 会同时记录 `declared_work_dir`、`workspace` 和实际 `work_dir`，排障和人工确认转发应优先使用 record 中的实际 `work_dir`。

`HANDOFF_FILES` 用于两个 `RUN_WORKFLOW` 之间的文件交接。`FROM` 指向上游 `RUN_WORKFLOW RESULT`，`COPY_FILE` / `COPY_DIR` 的源路径相对上游实际 `work_dir`，`AS` 目标路径相对父 `<work_dir>/.lgwf/handoff/<node_id>/`。`RESULT` 字段值是复制后文件或目录的绝对路径，保证下游隔离 child workflow 可直接读取；结果同时包含 `handoff_files` 对象，方便下游 `PY INPUT state.handoff_files` 读取。目录交接默认整体替换目标目录；不支持复制 `.lgwf`、绝对路径或 `..` 逃逸。

```text
HANDOFF_FILES spec_to_impl
  FROM state.pipeline.build_spec_result
  COPY_FILE "outputs/spec.json" AS "spec.json" FIELD spec_path
  COPY_DIR "generated" AS "generated" FIELD generated_dir
  RESULT state.pipeline.impl_input;
```

上例输出给下游 `RUN_WORKFLOW INPUT` 的对象为：

```json
{
  "spec_path": "D:/.../<parent-work-dir>/.lgwf/handoff/spec_to_impl/spec.json",
  "generated_dir": "D:/.../<parent-work-dir>/.lgwf/handoff/spec_to_impl/generated",
  "handoff_files": {
    "spec_path": "D:/.../<parent-work-dir>/.lgwf/handoff/spec_to_impl/spec.json",
    "generated_dir": "D:/.../<parent-work-dir>/.lgwf/handoff/spec_to_impl/generated"
  }
}
```

`workflow.json` 是 runtime IR，但用户 authoring package 默认不保存该文件。通过 `scripts/lgwf.py run` 运行时，client 先把 package 复制到 `<work_dir>\.lgwf\workflow\`，再在 snapshot 中生成 runtime IR。`workflow.json` 仍只使用 `src/lgwf/compiler/dsl_schema.json` 接受的字段：

```json
{
  "nodes": [],
  "edges": [],
  "routes": [],
  "entry_point": "node_id"
}
```

从 `src/lgwf/capabilities/catalog.json` 选择 runtime capability。不要靠猜测新增 DSL 字段。Authoring DSL v2 使用 `PY`、`CODEX`、`APPROVAL`、`REVIEW`、`HANDOFF`、`RUN_WORKFLOW`、`REACT`、`AGENT_LOOP` 高层声明 lowering 到现有 runtime JSON IR；不新增 runtime 内置业务 mapper。

`CODEX` 小型结构化结果可用 `OUTPUT_JSON "path.json"`；大 JSON 使用 `OUTPUT_JSON "path.json" AS_FILE`，由 Codex 写文件，LGWF runner 验证文件存在、UTF-8、JSON 可解析且顶层是 object。通用文本 artifact 使用 `OUTPUT_FILE "path"`，由 Codex 写文件，runner 验证文件存在、UTF-8 可读并记录路径和大小，不解析内容。

需要让同一个 Codex 逻辑节点在循环中复用上下文时，可在 `CODEX` 内声明 `KEEP_SESSION`。该标志只复用 Codex CLI session id，不保活进程；scope 由 runtime 自动按普通 node、`REACT` slot 或 `AGENT_LOOP` slot 推导。典型用途是 `REACT` 的 `REASON CODEX KEEP_SESSION`，让下一轮 reason 能延续上一轮 observe 反馈的会话上下文。需要让同一个 `workflow.lgwf` 内多个 Codex 节点或 slot 共享 session 时，使用 `KEEP_SESSION GROUP "name"`；group 不跨父 workflow、`STEP ... WORKFLOW` 子 workflow 或 `RUN_WORKFLOW` 子进程，同一 workflow 内同名 group 会共享。

`APPROVAL` 只表达二元人工审批，route key 只能是 `approve` / `reject`。需要 `approve` / `revise` / `reject` 或“小改后再确认”时使用固定三选项的 `REVIEW`；`REVIEW CONTEXT state.*` 必须指向 JSON object，并在 `FLOW` 中把 `revise` 接回修订节点或当前评审节点。不要在 `.lgwf` 或 `workflow.json` 中写入 Agent Host、`main_agent`、`session_id`、controller payload、approval worker/window 或 CLI 调用；这些属于 `lgwf_client.main_agent` 控制面和执行 agent loop。

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
- 对于 Codex 真正要分析的用户授权目标目录或文件，使用 `target_dirs` / `target_files`，或 Authoring DSL 的 `TARGET_DIR` / `TARGET_FILE` / `TARGET_DIRS state.*` / `TARGET_FILES state.*`；这些字段只表达可读分析范围，不表达写权限。不要把动态分析目标塞进 `context_refs`。
- 对于 Codex 允许修改的目录，使用 `edit_dirs` 或 Authoring DSL 的 `EDIT_DIR` / `EDIT_DIRS state.*`。`EDIT_DIR(S)` 也隐含可读；未落入 `EDIT_DIR(S)` 的 `TARGET_DIR(S)` 只能分析，不能修改。
- `target_dirs` / `target_files` / `edit_dirs` 可使用绝对路径，由 client runner 校验存在性和文件/目录类型；它们不是 workflow resource refs。
- 生成 prompt 文件时，不在本文件展开 prompt 规则；读取 `references/prompt-assist/guide.md`，并保持 prompt 的 `Inputs` 与 `context_refs` 对齐。
- 省略 `cwd`，让执行默认发生在 workspace root。

## 常用 Capability

- `exec.run_shell`：在 client 上运行 shell command。
- `exec.run_python`：在 client 上运行 inline Python 或 script reference。
- `exec.codex_prompt`：使用内联 prompt 或 `prompt_ref` 运行 Codex。
- `flow.if`、`flow.switch`、`flow.guard`、`flow.assign`：控制 state 和 routing。
- `flow.run_workflow`：运行期同步调度独立 child workflow package；authoring 时使用 `RUN_WORKFLOW`。
- `subgraph.react`：固定 reason / act / observe / decide loop。
- `subgraph.agent_loop`：工程化 Agent Loop，包含显式状态、每轮 sandbox、验证、决策、归档、报告、`TOKEN_MAX` 和人工接管控制策略；authoring 时使用 `AGENT_LOOP`。
- `subgraph.workflow`：执行 compiler 嵌入的完整 workflow JSON IR；authoring 时使用 `STEP ... WORKFLOW`。

`subgraph.react` 和 `subgraph.agent_loop` 中的 prompt 设计职责由 `references/prompt-assist/guide.md` 处理：`reason` / `diagnose` / `plan` 使用 Draft Prompt，`act` 使用 Action Prompt，`observe` 使用 Audit Prompt，`decide` 默认优先脚本或轻量节点。不属于 Draft、Action 或 Audit 职责的普通 `exec.codex_prompt` 使用 Normal Prompt。

`AGENT_LOOP` 默认向内部 Codex slot 注入 `target_dirs_path="targets.dirs"`、`target_files_path="targets.files"` 和 `edit_dirs_path="targets.edit_dirs"`，slot 内不要声明 `TARGET_DIRS` / `TARGET_FILES` / `EDIT_DIRS` 覆盖。运行时 `exec.codex_prompt` 会写节点级 `state.token_usage.<node_id>`；全局累计和用时由 runtime metrics 写入 `state.run.token_usage` 和 `state.run.node_timings`。`TOKEN_MAX` 默认 `1000000`，在准备进入下一轮之前判断，达到预算后进入 `waiting_human`。

除非任务明确要求架构工作，否则不要新增 `flow.join`、parallel fan-in 或新的 DSL schema 字段。

对于 ReAct decide slot，如果脚本需要写入 `next=continue` 或 `next=exit`，优先使用 `UPDATES_STATE { WRITE state.<decision_path>; }`，脚本必须打印一个 JSON object，其中 key 是 runtime state path。旧的裸 `UPDATES_STATE` / `state_updates_from_stdout=true` 仍兼容，但不会检查 stdout patch 具体写入范围。

## 最小检查

创建 workflow 后运行：

```powershell
python <skill-dir>\scripts\lgwf.py audit <package-root>\workflow.lgwf
.venv\Scripts\python.exe -m unittest discover -s test -p "test_*.py"
.venv\Scripts\python.exe -m compileall -q src test
```

如需 workflow 专属编译和运行检查，先运行 `scripts/lgwf.py audit <package-root>\workflow.lgwf` 修复 authoring diagnostics，再使用 `scripts/lgwf.py run --workflow-lgwf`。facade 会在 `<work_dir>\.lgwf\workflow\` snapshot 中再次 audit、compile 和运行，确保 runtime `workflow` root 与复制后的资源路径一致，同时不污染用户 package。
