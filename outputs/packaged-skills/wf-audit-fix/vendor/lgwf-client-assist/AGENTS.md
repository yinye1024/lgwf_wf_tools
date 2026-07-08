# LGWF Client Assist

LGWF 对外唯一 Agent skill。识别任务类型，加载对应 reference，并统一通过 `scripts/lgwf.py` 调用底层实现。

## 路由

### 第一次使用或确认环境

用户要求“初始化 LGWF”“检查能否运行”“验证安装或 wheel”“跑 smoke test”时：

1. 读取 `references/workflow-usage.md` 中的 Doctor 和 Smoke Test。
2. 使用 `scripts/lgwf.py doctor` 检查 Python、bundled wheel、已安装模块和可选输入路径。
3. `doctor` 只做诊断，不安装；执行 smoke test 或业务 workflow 时，`scripts/lgwf.py run` 会自动安装随 skill 分发的 wheel。

### 直接运行一个 Workflow

用户已经提供 `workflow.json` 或 `workflow.lgwf`，并要求执行、重跑或保存结果时：

1. 读取 `references/workflow-usage.md`，确认输入类型、独立 `work_dir`、旧运行数据处理方式和输出要求。
2. 使用 `scripts/lgwf.py run`；它会自动安装 bundled wheel，不要求先运行 `doctor`。
3. 传入 `.lgwf` 时由 facade 在 workspace snapshot 中完成 audit、compile 和运行；不要先在用户 package 中生成 `workflow.json`。
4. 只有用户明确要求诊断环境时使用 `doctor`；只有明确要求单独生成 runtime IR 时使用 `compile`。

### 运行长任务或包含 Human Approval 的 Workflow

用户要求持续跟踪进度，或 workflow 可能包含长时间节点、后台运行、human approval 时：

1. 在启动前读取 `references/agent-host-assist/guide.md` 和 `references/agent-host-assist/cli-agent-loop.md`，同时读取 `references/workflow-usage.md`。
2. 使用 `scripts/lgwf.py run` 后保存同一个 workflow handle，不把启动命令当作一次性任务。
3. 使用 `scripts/lgwf.py status` 和 `wait` 持续跟踪；等待确认时使用 `scripts/lgwf.py approval` 在当前对话完成用户确认；结束后使用 `scripts/lgwf.py runs` 查询 summary 和 changed files。
4. 除非用户明确要求停止或重跑，否则不要丢弃当前 handle、启动新 workflow 或退出等待中的 workflow loop。

### 继续或重跑已有 Work Dir

用户指定的 `work_dir` 已包含 `.lgwf` 运行数据，或 facade 返回需要选择 `continue` / `rerun` 时：

1. 读取 `references/workflow-usage.md` 中的旧运行数据处理规则。
2. 向用户明确询问继续现有 workflow 还是清理后重跑；不要自行选择。
3. `continue` 后沿用现有 handle 并进入长任务跟踪场景；`rerun` 时仍通过 `scripts/lgwf.py run`，由 work-dir guard 验证后清理。

### 创建或修改 Workflow Package

用户要求新建 workflow、调整目录、增加 step/sub-workflow、修改 DSL 或使用 client tools 时：

1. 读取 `references/dsl-assist/guide.md` 和 `references/dsl-assist/create-workflow.md`。
2. 涉及原生 `TOOL` 节点时再读取 `references/dsl-assist/tool-nodes.md`，并可用 `scripts/lgwf.py tool list|describe` 查询公开工具。
3. 涉及 prompt 资源时同时进入 prompt 场景，只加载对应 prompt 类型规则。
4. 修改后使用 `scripts/lgwf.py audit`；需要端到端验证时再使用 `scripts/lgwf.py run --workflow-lgwf`。

### 审计或验收 Workflow

用户要求检查、review、audit 或修复已有 workflow package 时：

1. 读取 `references/dsl-assist/guide.md` 和 `references/dsl-assist/workflow-audit-checklist.md`。
2. 使用 `scripts/lgwf.py audit` 获取机器可读 diagnostics，修复明确问题后重复 audit。
3. 如果包含 prompt，追加读取 `references/prompt-assist/guide.md` 和 prompt audit checklist。
4. 用户只要求审计时只报告问题；用户要求修复时才修改文件并做最小运行验证。

### 创建、优化或验收 Prompt

用户要求处理 prompt 文件，或 workflow 的 `CODEX` / `REACT` 节点引用 prompt 时：

1. 读取 `references/prompt-assist/guide.md`，先识别 Draft、Action、Audit、Normal 或 Decide。
2. 只加载对应类型 reference 和 `shared-rules.md`；验收 prompt 时再加载 `prompt-audit-checklist.md`。
3. prompt 属于 workflow 时，同时读取对应 DSL node config，核对 inputs、outputs 和 context refs。
4. 修改 workflow prompt 后使用 `scripts/lgwf.py audit` 检查整体对齐；独立普通 prompt 不强制运行 workflow audit。

### 排查执行、CLI 或 Runner 问题

用户报告 workflow 失败、状态异常、CLI 输出不符预期、runner 或 client tool 执行异常时：

1. 读取 `references/runtime-assist/guide.md`，先收集输入路径、`work_dir`、stderr、status 和 run records。
2. 按问题使用 `scripts/lgwf.py doctor`、`status`、`runs` 或 `tool`，先判断是环境、运行状态、DSL、prompt 还是 runner 问题。
3. 根因属于 DSL 或 prompt 时转入对应场景，不在 runtime 排障中改写其业务规则。
4. facade 无法提供足够信息时，再读取 `references/compatibility-cli.md`，使用旧 CLI 做兼容验证或底层排障。

## 全局约束

- 常规操作统一使用 `scripts/lgwf.py`。
- 仅在兼容或底层排障时使用旧 CLI。
- 按任务读取 reference，不要一次加载全部内容。
