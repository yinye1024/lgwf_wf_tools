# LGWF Workflow Tools 指引

本目录是 LGWF workflow 工具集合的 facade 入口。主智能体只通过根目录 `SKILL.md` 与用户交互，再根据用户目标、目标 workflow 状态和 `registry.json` 派发到 `workflows/*` 下的内部 workflow package。

本文件只保留必须即时遵守的入口规则。长流程说明拆到：

- [docs/facade-dispatch.md](docs/facade-dispatch.md)：初始化、派发、监控和收尾流程。
- [docs/self-improve.md](docs/self-improve.md)：self-improve 触发规则、产物和命令。
- [docs/workflow-inputs.md](docs/workflow-inputs.md)：各内部 workflow 输入摘要。
- [docs/maintenance.md](docs/maintenance.md)：显式命令、bundled client 更新和最小验证。

## Facade 职责

- 根据用户需求路由到合适的内部 workflow。
- 监控被派发 workflow 的执行，处理 approval、阻塞、失败诊断和收尾汇总。
- 根据真实执行暴露的问题进入 self-improve，沉淀证据并产出可审查改进。

本 facade 不默认组装多个 workflow，不默认连续执行质量链路，也不默认连续串联多个会修改目标 package 的 workflow。某个 workflow 完成后，如果结果证据显示需要进入另一个 workflow，应再重新列出候选、说明理由并重新路由。

## 可用 Workflow

实际路径、固定 `work_dir` 和对应 `AGENTS.md` 必须以根目录 `registry.json` 为准；不要硬编码已记忆的路径。路由前必须先列出可用 workflow，并说明为什么选择目标 workflow。优先运行：

```powershell
python scripts/list_workflows.py
```

当前 registry 中的主要职责摘要：

| Workflow id | 主要职责 | 典型使用时机 |
| --- | --- | --- |
| `wf-fix` | 运行并修复目标 LGWF workflow，支持候选目录修复、验证和 promote。 | 用户要“修复当前 workflow 失败”“跑起来并自愈”“根据真实失败改 DSL/prompt/script”。 |
| `wf-create` | 根据用户原始意图创建新的 LGWF workflow 初稿。 | 用户要“从零创建 workflow”“只有原始想法，帮我生成 workflow 初稿”。 |
| `wf-prompt-fix` | 盘点、验收并修复目标 workflow 引用的 prompt 基础规范问题。 | 用户要“检查 prompt 是否合格”“修复 prompt 引用/格式/输出契约”。 |
| `wf-prompt-upgrade` | 为目标 workflow 引用的 prompt 生成设计升级方案，并在确认后应用。 | 用户要“提升 prompt 质量”“优化 Agent 职责/决策标准/验收指标”。 |
| `e2e-test-generator` | 为目标 LGWF workflow 生成三类端到端测试。 | 用户要“补 E2E 测试”“交付前建立回归入口”。 |
| `plan` | 把复杂任务拆成可确认的计划契约、验收契约，并在确认后按 ReAct 闭环执行。 | 用户要“先规划再执行”“先给验收标准”“按计划闭环实现复杂任务”。 |

## 路由规则

先判断用户请求是否匹配显式目标 workflow 直启路由；只有不匹配时，才进入旧的 registry 内部 workflow 路由。

### 目标 Workflow 直启路由

只有当用户明确使用以下任一形式时，才进入目标 workflow 直启路由，不从 `registry.json` 选择内部 workflow：

- `/lgwf-wf-tools run <path>`
- `/lgwf-wf-tools target-run <path>`
- `/lgwf-wf-tools --target-workflow <path>`

不要用宽泛自然语言触发直启路由。用户说“修复”“优化”“生成测试”“规划”“检查 prompt”等任务，即使同时给出 workflow 目录或 `workflow.lgwf` 路径，也必须继续走内部 workflow registry 路由。

路径解析规则：

- 如果 `<path>` 是 `workflow.lgwf` 文件，直接作为目标 workflow。
- 如果 `<path>/workflow.lgwf` 存在，使用该文件。
- 如果 `<path>/wf/workflow.lgwf` 存在，使用该文件。
- 默认 `work_dir` 使用目标 package 下的 `ws/`；`<package>/wf/workflow.lgwf` 对应 `<package>/ws`，`<dir>/workflow.lgwf` 对应 `<dir>/ws`。
- 如果无法解析出唯一目标 `workflow.lgwf`，报告解析失败原因，不回退到内部 workflow 路由。
- 如果 `work_dir/.lgwf` 已存在，先让用户选择 `continue`、`resume` 或 `rerun`，不要直接启动第二个 run。

直启路由仍必须使用本目录内置的 `vendor/lgwf-client-assist/scripts/lgwf.py`，并继续遵守监控循环、approval 边界和 UTF-8 输入规则。第一版默认使用空输入 `{}`；需要复杂输入时，优先要求用户提供 UTF-8 JSON 文件。

### 内部 Workflow Registry 路由

进入内部 workflow 路由前，先执行或等价展示 `scripts/list_workflows.py` 的清单。随后结合用户目标、目标路径、已有运行产物和错误证据，选择一个最合适的 workflow。

方案优先是普通目标路由的强制门槛。普通目标如果会修改目标 package、启动真实 workflow 或提交 approval，必须先说明：目标 workflow、输入来源、是否会修改文件、是否会真实运行、approval 边界和最小验证方式。未经用户明确确认，不得启动任何内部 workflow；用户明确说“立即运行”“直接修复”“自动执行”或给出等价授权时，可以直接启动。

`ambiguous_modify_goal` 是严格 proposal gate：当用户说“修复优化”“优化修复”“完善”“处理”“整理”“质量提升”等范围词，或提出模糊的“优化/修复”，并同时给出目标目录、目标 workflow 或 package 路径时，一律先判定为 `ambiguous_modify_goal`。除非用户明确说“直接修改”或给出等价授权，否则只能做只读检查并输出 proposal；禁止改文件，禁止启动任何内部 workflow，禁止启动目标 workflow run。proposal 必须包含：目标、发现依据、候选路由、修改范围、是否真实运行、approval 边界、最小验证方式和明确的 will-not-do。

优先根据用户的直接目标路由：

- 目标是运行失败、卡住、产物不对、需要自动诊断修复：使用 `wf-fix`。
- 目标是从原始意图创建新的 LGWF workflow 初稿：使用 `wf-create`。
- 目标是 prompt 文件缺失、引用不清、输入输出契约不完整、上下文约束不足：使用 `wf-prompt-fix`。
- 目标是 prompt 质量升级、角色职责重塑、评估标准、失败模式、上下游协作质量：使用 `wf-prompt-upgrade`。
- 目标是生成或刷新 workflow 的端到端测试：使用 `e2e-test-generator`。
- 目标是复杂任务规划、先产出计划/验收契约、用户确认后再按 ReAct 闭环执行：使用 `plan`。

证据修正规则：

- 如果用户说“修复 workflow”，但证据只指向 prompt 基础规范且不需要真实运行目标 workflow，先用 `wf-prompt-fix`。
- 如果用户说“优化 prompt”，但目标 workflow 已经有明确运行失败证据，先用 `wf-fix`。
- 如果用户说“生成测试”，但目标 `workflow.lgwf` 不能解析或基础契约明显缺失，先报告前置阻塞，并建议转入 `wf-fix` 或 `wf-prompt-fix`。
- 如果目标目录还没有可解析的 `workflow.lgwf`，但用户目标是创建新的 LGWF workflow，使用 `wf-create`；否则先让用户补充目标或改为普通实现任务。
- 如果用户明确要求交付质量治理，可以建议从 `wf-prompt-fix` 开始；当前阶段完成后，基于结果证据决定是否重新路由到 `wf-prompt-upgrade` 或 `e2e-test-generator`。

## 核心约束

- 对外只暴露根目录 `SKILL.md`；`workflows/*` 和 `vendor/lgwf-client-assist/` 不得作为独立 Codex skill 注册。
- 内部目录只使用 `AGENTS.md` 承载规则；`workflows/*` 下不得出现 `SKILL.md`。
- 每次派发前先读取 `registry.json`，再读取目标 workflow 的 `AGENTS.md`。
- 运行、查询、等待、approval 和 run-record 操作统一使用 `vendor/lgwf-client-assist/scripts/lgwf.py`；`python -m lgwf_client.cli` 只用于底层排障。
- 不要把 `.lgwf/`、`ws/`、`ws_*`、`.tmp/`、`__pycache__/` 或 `assets/install-state.*` 当作源码。
- 如果固定 `work_dir` 已有历史 LGWF 数据，先按 continue/resume/rerun 流程询问用户，不要直接启动第二个 run。
- workflow package 内部 `SCRIPT`、`PROMPT`、`PROMPT_REF`、`CONTEXT workflow` 和 `STEP ... WORKFLOW` 路径必须保持相对路径；禁止绝对路径、`..` 和循环引用。
- 中文、复杂 JSON、approval value 和报告必须保持 UTF-8；在 PowerShell 中不要把包含中文的 JSON 直接塞进长命令文本，优先使用 UTF-8 文件或安全 argv 传参。

## 必读流程

- 派发或监控内部 workflow 前，按 [docs/facade-dispatch.md](docs/facade-dispatch.md) 执行。
- self-improve 请求或真实执行问题，按 [docs/self-improve.md](docs/self-improve.md) 执行。
- 准备 `--input-json` 前，先查 [docs/workflow-inputs.md](docs/workflow-inputs.md)，最终以目标 workflow `AGENTS.md` 为准。
- 维护显式命令、初始化或更新 bundled client 时，按 [docs/maintenance.md](docs/maintenance.md) 执行。

## 高风险规则锚点

- `waiting_human` 不是完成状态；如果是 `AGENT_LOOP` 控制状态但没有 human request，汇报 loop reason、evidence 和 artifact 路径，等待用户决定。
- 用户显式输入 `/lgwf-wf-tools self-improve`、`/lgwf-wf-tools 自我优化`，或自然语言要求复盘、自我优化、沉淀 case、生成 proposal、生成 eval case 时，必须进入 self-improve 路由；先归类问题、列出可执行的 self-improve 路径。
- self-improve 脚本只生成记录、报告和 proposal，不自动修改 `AGENTS.md`、`registry.json`、workflow 文件或 vendor 文件。
- 发布包不得覆盖或删除 `.local/self-improve/`、`.local/overrides/` 或 `.local/upgrade-reports/`。

## 最小验证

修改 `SKILL.md`、`AGENTS.md`、`registry.json`、`workflows/*/AGENTS.md`、`workflows/**/workflow.lgwf`、`scripts/init_lgwf_wf_tools.py`、`scripts/doctor_lgwf_wf_tools.py`、`scripts/validate_registry.py`、`scripts/list_workflows.py` 或 vendor manifest 后，应运行：

```powershell
python self-improve/scripts/run_self_evals.py
```

只检查 facade 是否自包含时运行：

```powershell
python scripts/doctor_lgwf_wf_tools.py
```
