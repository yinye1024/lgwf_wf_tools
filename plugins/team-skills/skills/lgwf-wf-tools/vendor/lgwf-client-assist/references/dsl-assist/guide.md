# LGWF Workflow 辅助

用于创建和修改 workflow 目录。它只处理 workflow 目录结构、DSL、capability 配置和资源引用；prompt 文件的具体设计规范读取 `references/prompt-assist/guide.md`。

## 创建或修改 Workflow

1. 读取目标 workflow 目录或预期目录；如果存在根 `workflow.lgwf`，优先读取它。
2. 读取 `references/dsl-assist/create-workflow.md`；涉及稳定 client 工具时再读取 `references/dsl-assist/tool-nodes.md`。
3. 如果涉及 `prompt.md`、`refine.md`、review prompt、`exec.codex_prompt`、`subgraph.react` 或 `subgraph.agent_loop` 的 Codex slot，再读取 `references/prompt-assist/guide.md` 并按它的分流规则读取对应 reference。

## 验收 Workflow

1. 读取目标 workflow 目录的根 `workflow.lgwf`、README 和直接业务子目录；用户 authoring package 默认不保存生成的 `workflow.json`。
2. 读取 `references/dsl-assist/workflow-audit-checklist.md`。
3. 优先运行 `scripts/lgwf.py audit <workflow.lgwf>`，读取 JSON diagnostics；按 `code`、`location`、`message`、`suggestion` 修复明确违反规范的文件，再重复运行 audit，直到 `passed=true` 或只剩用户需确认的问题。
4. 如果涉及 prompt 文件，再读取 `references/prompt-assist/guide.md` 和 `references/prompt-assist/prompt-audit-checklist.md`。
5. 按 checklist 输出问题并修复明确违反规范的文件，除非用户只要求审计不修改。

## 核心边界

- workflow 目录是用户提供 workflow 的主模型。
- 创建或维护 workflow 目录时，新建或重写的 README、prompt、人工确认说明、报告模板等面向人阅读的文本正文默认使用中文；代码、JSON key、YAML key、DSL capability 名称、文件路径、命令、API 字段、错误码和协议字段不翻译。
- 包含 `workflow.lgwf` 的业务目录是 workflow；不包含 `workflow.lgwf` 的业务目录是普通 step。
- 不使用固定的 `steps/`、`workflows/` 或 `rules/` 容器；当前 workflow 的直接子目录按业务职责和阶段命名。
- 当前 `workflow.lgwf` 直接声明普通 step 的执行节点，并通过 `STEP ... WORKFLOW` 引用需要独立拓扑、复用或嵌套编排的子 workflow。
- 普通 step 只保存自己的 `agents/`、`scripts/` 等资源；多个直接子级共用的资源放在当前 workflow 的 `shared/`。
- `workflow.json` 是编译产物、runtime IR 和执行入口，必须能由 `scripts/lgwf.py compile` 从根 `.lgwf` 生成；通过 facade 运行时只保存在 `<work_dir>/.lgwf/workflow/` snapshot，不写入用户 package。
- 子 workflow 可递归包含普通 step 和更深层子 workflow；父 workflow 不复制子 workflow 的内部节点。
- authoring resource 和 workflow reference 路径相对当前 `workflow.lgwf` 所在目录，编译后统一转换为 package-root 相对路径。
- workflow package 与 `--work-dir` 不能是同一目录；work dir 位于 package 内部时由 snapshot 复制逻辑整体排除。`data/`、`reports/`、`.lgwf/` 等 workspace 输入、输出和运行状态不放入 package。
- runtime 不读取 client workspace 中的 prompt/script 内容。
- `prompt_ref` / `script_ref` 必须作为 node config 传给 client。
- resource path 必须是相对路径，不允许绝对路径或 `..`。
- `decide` 默认优先脚本或轻量节点，不默认设计成 LLM prompt。
- 工程化长程循环优先使用 `AGENT_LOOP`。它 lowering 到 `subgraph.agent_loop`，内建每轮 sandbox、状态、归档、验证、决策、`TOKEN_MAX` 和 `ON_MAX` / `ON_ERROR` 控制策略；普通轻量 reason / act / observe / decide 循环仍可使用 `REACT`。

## 验证

创建或修改 workflow 后，优先做静态和最小运行检查：

```powershell
.venv\Scripts\python.exe -m lgwf_dsl.cli audit <workflow_lgwf>
.venv\Scripts\python.exe -m unittest discover -s test -p "test_*.py"
.venv\Scripts\python.exe -m compileall -q src test
```

端到端 smoke 优先参考 `examples/workflows/shell_smoke`，通过 `scripts/lgwf.py run --workflow-json <workflow.json> --work-dir <dir>` 本地执行；不要为了 smoke test 新增 runtime 侧目录 loader。
