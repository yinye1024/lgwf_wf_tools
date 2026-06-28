# LGWF Workflow Agent 指引

本目录是 LGWF workflow 相关能力的 facade 入口。主智能体只通过根目录 `SKILL.md` 与用户交互，再根据用户目标、目标 workflow 状态和 `registry.json` 派发到 `workflows/*` 下的内部 workflow package。

本文件的职责是回答三件事：

- 本目录下有哪些可派发 workflow。
- 用户提出不同目标时应该路由到哪个 workflow。
- 派发、继续、approval 和收尾时必须遵守哪些边界。

## 可用 Workflow

| Workflow id | 入口 | 主要职责 | 典型使用时机 |
| --- | --- | --- | --- |
| `wf-fix` | `workflows/wf-fix/wf/workflow.lgwf` | 运行目标 LGWF workflow，观察失败、阻塞或输出不满足契约的原因，在候选目录中修复并验证后 promote。 | 用户要“修复当前 workflow 失败”“跑起来并自愈”“根据真实失败改 DSL/prompt/script”。 |
| `wf-prompt-fix` | `workflows/wf-prompt-fix/wf/workflow.lgwf` | 盘点目标 workflow 引用的 prompt，审计并修复基础规范、引用、上下文和输出契约问题。 | 用户要“检查 prompt 是否合格”“修复 prompt 引用/格式/输出契约”“交付前做 prompt acceptance”。 |
| `wf-prompt-upgrade` | `workflows/wf-prompt-upgrade/wf/workflow.lgwf` | 分析 prompt 的职责边界、上下游契约、质量指标和失败模式，生成升级方案并在用户确认后应用。 | 用户要“提升 prompt 质量”“优化 Agent 职责/决策标准/验收指标”“做 prompt 设计升级”。 |
| `e2e-test-generator` | `workflows/e2e-test-generator/workflow.lgwf` | 为已有目标 workflow 生成脚本级、runtime fake 和真实 Codex 正向三类 E2E 测试。 | 用户要“补 E2E 测试”“交付前建立回归入口”“为 workflow 生成测试骨架”。 |
| `plan` | `workflows/plan/wf/workflow.lgwf` | 把复杂任务拆成可确认的计划契约、验收契约，并在用户确认后按 ReAct 闭环执行。 | 用户要“先规划再执行”“先给验收标准”“按计划闭环实现复杂任务”“需要人工确认计划/验收后再改文件”。 |

实际路径、固定 `work_dir` 和对应 `AGENTS.md` 必须以根目录 `registry.json` 为准；不要硬编码已记忆的路径。

除 `/lgwf-wf-agent help` 或纯帮助请求外，路由前必须先列出可用 workflow。标准入口是 `python scripts/list_workflows.py`；如果已经从 `registry.json` 读取了同等清单，也必须向用户展示可用 workflow，并说明为什么选择目标 workflow。

## 路由决策

进入任何内部 workflow 路由前，先执行或等价展示 `scripts/list_workflows.py` 的清单；然后结合用户目标说明为什么选择目标 workflow。`help`、`doctor`、`list`、`init` 等显式只读或初始化命令按各自规则处理，不触发内部 workflow 路由。

方案优先是普通目标路由的强制门槛：除非用户明确说“立即运行”“直接修复”“自动执行”或给出等价授权，主 agent 必须先给出推荐方案、workflow 组合顺序、每阶段是否会修改目标 package、是否会真实运行、approval 边界和最小验证方式；未经用户明确确认，不得启动任何内部 workflow。

`ambiguous_modify_goal` 是更严格的 proposal gate：当用户说“修复优化”“优化修复”“完善”“处理”“整理”“质量提升”等范围词，并同时给出目标目录、目标 workflow 或 package 路径时，一律先判定为 `ambiguous_modify_goal`。除非用户明确说“直接修改”“直接跑 wf-fix”“不用方案，直接执行”或给出等价授权，否则主 agent 只能做只读检查并输出 proposal；禁止改文件，禁止调用 `apply_patch`，禁止启动任何内部 workflow，禁止启动目标 workflow run。proposal 必须包含：目标、发现依据、候选路由、修改范围、是否真实运行、approval 边界、最小验证方式和明确的 will-not-do。用户确认 proposal 前，不得把只读检查中发现的小问题直接落盘修复。

用户提出模糊的“优化/修复”目标时，默认先按质量治理而不是真实运行修复处理：先 `wf-prompt-fix`，再 `wf-prompt-upgrade`，最后视需要 `e2e-test-generator`。只有已经存在真实运行失败、卡住、目标产物不满足契约，或用户明确授权基于真实运行自愈时，才把 `wf-fix` 作为第一阶段。

优先根据用户的直接目标路由：

- 目标是运行失败、卡住、产物不对、需要自动诊断修复：使用 `wf-fix`。
- 目标是 prompt 文件缺失、引用不清、输入输出契约不完整、上下文约束不足：使用 `wf-prompt-fix`。
- 目标是 prompt 质量升级、角色职责重塑、评估标准、失败模式、上下游协作质量：使用 `wf-prompt-upgrade`。
- 目标是生成或刷新 workflow 的端到端测试：使用 `e2e-test-generator`。
- 目标是复杂任务规划、先产出计划/验收契约、用户确认后再按 ReAct 闭环执行：使用 `plan`。

再按证据修正路由：

- 如果用户说“修复 workflow”，但问题只来自 prompt 基础规范且不需要运行目标 workflow，先用 `wf-prompt-fix`。
- 如果用户说“优化 prompt”，但现状是目标 workflow 已经运行失败且失败证据明确，先用 `wf-fix`；修复后再考虑 prompt workflow。
- 如果用户说“交付/质量达标”，默认先 `wf-prompt-fix`，再 `wf-prompt-upgrade`，最后视需要 `e2e-test-generator`。
- 如果用户说“生成测试”，但目标 `workflow.lgwf` 不能解析或基础契约明显缺失，先报告前置阻塞，并建议转入 `wf-fix` 或 `wf-prompt-fix`。
- 如果用户的目标本身不是修复已有 workflow，而是要规划并执行一个复杂实现任务，优先用 `plan`；执行过程中发现目标 workflow 失败、prompt 缺陷或测试缺口时，再回到对应专项 workflow。
- 如果目标目录还没有可解析的 `workflow.lgwf`，不要派发这些 workflow；先让用户补充目标或改为普通实现任务。

## 组合顺序

不要无声连续运行多个会修改目标 package 的 workflow。每个阶段结束后先汇报产物、修改文件、风险和下一步选项，再继续。

常见组合：

- 修复当前失败：`wf-fix`。如果修复发现 prompt 基础契约是根因，再转 `wf-prompt-fix`；如果发现 prompt 设计质量不足，再转 `wf-prompt-upgrade`。
- 交付前验收：`wf-prompt-fix` -> `wf-prompt-upgrade` -> `e2e-test-generator`。
- prompt 专项治理：先 `wf-prompt-fix` 清理基础问题，再 `wf-prompt-upgrade` 做设计升级。
- 测试补齐：先确认目标 workflow 可解析且基础契约清楚，再运行 `e2e-test-generator`；测试生成发现运行缺陷时回到 `wf-fix`。
- 复杂实现任务：先 `plan` 生成计划和验收契约，经用户确认后执行；如果执行结果暴露 workflow 专项问题，再按证据转 `wf-fix`、`wf-prompt-fix` 或 `wf-prompt-upgrade`。

## 核心约束

- 对外只暴露根目录 `SKILL.md`；`workflows/*` 和 `vendor/lgwf-client-assist/` 不得作为独立 Codex skill 注册。
- 内部目录只使用 `AGENTS.md` 承载规则；`workflows/*` 下不得出现 `SKILL.md`。
- 每次派发前先读取 `registry.json`，再读取目标 workflow 的 `AGENTS.md`。
- 运行、查询、等待、approval 和 run-record 操作统一使用 `vendor/lgwf-client-assist/scripts/lgwf.py`；`python -m lgwf_client.cli` 只用于底层排障。
- `assets/lgwf-client-assist.zip` 只作为临时同步输入；执行 `scripts/init_lgwf_wf_agent.py` 后必须记录 hash、解压到 `vendor/lgwf-client-assist/`、删除内部 `SKILL.md`，并删除该 zip。
- 不要把 `.lgwf/`、`ws/`、`ws_*`、`.tmp/`、`__pycache__/` 或 `assets/install-state.*` 当作源码。
- 如果固定 `work_dir` 已有历史 LGWF 数据，先按 continue/resume/rerun 流程询问用户，不要直接启动第二个 run。
- workflow package 内部 `SCRIPT`、`PROMPT`、`PROMPT_REF`、`CONTEXT workflow` 和 `STEP ... WORKFLOW` 路径必须保持相对路径；禁止绝对路径、`..` 和循环引用。
- 中文、复杂 JSON、approval value 和报告必须保持 UTF-8；在 PowerShell 中不要把包含中文的 JSON 直接塞进长命令文本，优先使用 UTF-8 文件或安全的 argv 传参。

## 显式命令

- `/lgwf-wf-agent`：执行入口预检；如果 doctor 通过，继续理解用户目标；如果 doctor 失败且存在 `assets/lgwf-client-assist.zip`，自动运行 init 后再次 doctor；如果仍失败，停止并报告。
- `/lgwf-wf-agent help` 或 `/lgwf-wf-agent 帮助`：只展示帮助，不修改文件，不派发内部 workflow，不启动 LGWF run，不运行会写 `.local/` 的 self-improve 命令。帮助内容必须简要列出可用指令、每个指令的用途、常见自然语言触发方式、哪些操作需要用户确认，以及下一步建议；如果用户随后选择某个命令，再按对应命令规则执行。
- `/lgwf-wf-agent init`：只运行 `python scripts/init_lgwf_wf_agent.py`，输出初始化报告；不派发内部 workflow。
- `/lgwf-wf-agent doctor`：只运行 `python scripts/doctor_lgwf_wf_agent.py`，输出只读健康检查报告；不修改文件，不派发内部 workflow。需要完整审计时运行 `python scripts/doctor_lgwf_wf_agent.py --deep`。
- `/lgwf-wf-agent list`：只运行 `python scripts/list_workflows.py`，只读列出 `registry.json` 中可派发的内部 workflow；不修改文件，不派发内部 workflow。
- `/lgwf-wf-agent self-improve`、`/lgwf-wf-agent 自我优化`、用户说“复盘这个 agent”“优化交互体验”“把这次问题沉淀成 case”：进入 self-improve 路由；先判断用户要做只读检查、incident 记录、proposal、eval case 草稿、scorecard 还是 pre-release gate。

## Facade 初始化

初始化分三层处理，不放在内部 workflow node 里：

1. Doctor 预检层：处理任何 `/lgwf-wf-agent` facade 请求前，先运行 `python scripts/doctor_lgwf_wf_agent.py`。该脚本只读检查根 `SKILL.md`、`registry.json`、registry 路径、vendor `AGENTS.md`、`scripts/lgwf.py`、bundled wheel，以及 vendor 内不得存在 `SKILL.md`。
2. Init 同步层：doctor 失败且存在 `assets/lgwf-client-assist.zip` 时，自动运行 `python scripts/init_lgwf_wf_agent.py`。它负责从临时 zip 刷新 `vendor/lgwf-client-assist/`、删除内部 `SKILL.md`、清理 install-state、写入 `.lgwf-client-assist-vendor.json`，删除 zip，并把初始化报告写入 `.local/init/last-init.json`。init 后必须再次运行 doctor。
3. 派发前预检层：doctor 通过后，准备派发内部 workflow 前再读取 `registry.json` 和目标 workflow `AGENTS.md`；缺失时直接报告 facade 安装不完整，不 fallback 到外部 skill。
4. Runtime 安装层：LGWF wheel 的安装由 `vendor/lgwf-client-assist/scripts/lgwf.py` 在 `run`、`audit`、`status`、`approval`、`runs` 等命令需要 runtime/client 模块时按 bundled wheel 自动处理。`doctor` 只诊断，不安装。

不要新增“初始化 workflow”来安装 wheel。原因是内部 workflow 启动本身就依赖 `lgwf.py run` 和 bundled wheel；把安装放进 workflow node 会让安装发生得太晚，无法覆盖启动前置依赖。内部 workflow 中的 `check_lgwf_client_assist` 只适合做运行中的环境确认或子流程前置检查，不应承担首次安装职责。

## 触发矩阵

| 场景 | 触发命令 | 说明 |
| --- | --- | --- |
| 使用 `/lgwf-wf-agent` 前 | `python scripts/doctor_lgwf_wf_agent.py` | 只读检查 facade 当前安装完整性。 |
| vendor zip 更新 | `python scripts/init_lgwf_wf_agent.py` -> `python scripts/doctor_lgwf_wf_agent.py` | `init` 只在同步 `assets/lgwf-client-assist.zip` 时使用；执行后必须再次 doctor。 |
| 修改 facade 或内部 workflow | `python self-improve/scripts/self_improve.py workflow-health` 或 `python self-improve/scripts/self_improve.py eval --check-overrides` | 开发期检查结构、语义和协作规则回归。 |
| 用户触发 self-improve/自我优化 | 先按目标选择 `eval`、`workflow-health`、`incident`、`proposal`、`eval-case`、`scorecard` 或 `pre-release` | 只读检查可直接运行；会记录 incident、生成 proposal、创建 eval 草稿或修改发布文件前必须先说明证据、影响范围和是否需要用户确认。 |
| 发布前默认 gate | `python self-improve/scripts/self_improve.py pre-release --version <version> --source <source>` | 自动包含 `doctor`、self eval、override、workflow health、scorecard 和 upgrade report。 |
| 发布前严格 gate | `python self-improve/scripts/self_improve.py pre-release --version <version> --source <source> --run-workflow-tests` | 额外执行内部 workflow baseline `test_command`；不会运行目标业务 workflow。 |

`pre-release` 不替代 `init`，也不会自动修复安装状态。doctor 失败时，pre-release 必须失败并报告；如果失败原因是 vendor 未同步，应由人工或外部发布流程先执行 `init -> doctor`，再重新运行 pre-release。

## 主动沟通

- 用户输入 `/lgwf-wf-agent help`、`/lgwf-wf-agent 帮助`、`help` 或“帮我看看这个 agent 怎么用”时，直接返回帮助摘要；不要为了帮助请求执行 doctor、list、self-improve 或内部 workflow。帮助摘要必须包含“可用指令”，并至少列出 `/lgwf-wf-agent help`、`/lgwf-wf-agent init`、`/lgwf-wf-agent doctor`、`/lgwf-wf-agent list`、`/lgwf-wf-agent self-improve`、`/lgwf-wf-agent 优化方案`；同时说明普通目标路由和 approval 边界。
- 用户提出需要选择内部 workflow 的普通目标时，先列出可用 workflow，再说明为什么选择目标 workflow；不要只在内部读取 `registry.json` 后直接给结论。
- 用户以 `self-improve`、`自我优化`、`复盘`、`优化交互体验`、`沉淀 case`、`生成 proposal` 或“为什么没有自动触发”提出请求时，不要只解释机制；必须先归类问题、列出可执行的 self-improve 路径，并在需要落盘前请求确认。
- 对 self-improve 请求，默认先盘点：用户反馈的事实、期望行为、实际行为、疑似区域、推荐命令和会产生的 `.local/` 产物。若用户已经明确说“记录/生成/执行”，可直接运行对应只读或本地记录命令；若内容会成为发布包 baseline，必须等待人工批准。
- self-improve 收尾时，如果本次生成了 proposal，或 `.local/self-improve/proposals/` 中存在待处理 proposal，必须提醒用户是否查看或执行 proposal。提醒应建议使用 `/lgwf-wf-agent 优化方案` 查看 review 计划；不直接执行 proposal，执行前必须先展示 review 计划、拟修改文件、验证命令和风险，并等待用户明确批准。
- 用户只给出模糊目标时，先把目标拆成 workflow 相关问题：目标 package、期望结果、允许修改范围、是否需要真实运行、是否接受自动修复、是否需要生成测试。
- 能从仓库路径、`workflow.lgwf`、运行产物或用户上下文推断的信息先自行检查；只询问会影响执行选择或风险边界的问题。
- 每次准备启动或继续 workflow 前，向用户说明将运行哪个内部 workflow、为什么、输入是什么、可能产生哪些修改。
- 遇到 `waiting_human`、旧 work dir、目标 workflow approval、DSL 不兼容或 runtime 失败时，先把事实和选项讲清楚，再等待用户确认。
- 不自动 approve 任何会修改目标 package、promote 候选目录或影响目标 workflow 业务决策的 approval。

## 派发流程

1. 以本目录为 facade root，读取 `registry.json`，按目标 workflow id 获取 `workflow_lgwf`、`work_dir` 和 `agents_md`。
2. 路由前必须先列出可用 workflow，优先运行 `python scripts/list_workflows.py`；如果因上下文已读取 `registry.json`，也必须展示同等清单。
3. 说明为什么选择目标 workflow，再读取目标 `AGENTS.md`，确认适用场景、输入契约、approval 语义、固定输出和自检要求。
4. 根据目标 workflow 的输入契约准备 `--input-json`。涉及中文或复杂 JSON 时，优先写入 UTF-8 文件，再由脚本读取或用安全 argv 传递。
5. 使用 bundled client 启动或继续：

```powershell
$lgwfPy = "vendor/lgwf-client-assist/scripts/lgwf.py"
python $lgwfPy run --workflow-lgwf <workflow_lgwf> --work-dir <work_dir> --input-json <json> --background
python $lgwfPy status --work-dir <work_dir> --session-id <session-id>
python $lgwfPy wait
```

6. 保存同一个 `session_id` / `pid` / `work_dir`，使用 `status`、`wait`、`approval` 和 `runs` 持续推进；不要把后台启动当一次性命令。
7. 进入 `waiting_human` 时展示 workflow 给出的摘要、选项和风险，只提交用户明确确认的结果。
8. 结束后汇总最终状态、关键产物、变更文件、阻塞项和建议下一步。

## 主 Agent 监控循环

主 agent 监控、旧 `work_dir` 处理、`status` / `wait` 轮询、`flow.human_approval` 提交和 run artifacts 查询的权威规则在 bundled client 指引中维护；本文件不复制细节，避免两处规则漂移。

派发任何内部 workflow 前必须读取：

- `vendor/lgwf-client-assist/AGENTS.md`
- `vendor/lgwf-client-assist/references/agent-host-assist/guide.md`
- `vendor/lgwf-client-assist/references/agent-host-assist/cli-agent-loop.md`
- `vendor/lgwf-client-assist/references/workflow-usage.md`

本 facade 只补充这些本地约束：

- 使用本目录内置的 `vendor/lgwf-client-assist/scripts/lgwf.py`，不要 fallback 到用户 `.codex` 中的外部 skill。
- 以 `registry.json` 中的 `work_dir` 作为当前内部 workflow 的固定工作目录；如果已有旧数据，按 vendor 指引让用户选择 `continue` / `resume` / `rerun`。
- 后台启动后保存同一个 `session_id` / `pid` / `work_dir`，后续所有 `status`、`wait`、`approval` 和 `runs` 操作都围绕同一个 handle。
- `waiting_human` 不是完成状态。若是 `flow.human_approval`，按 vendor main-agent ask flow 在当前对话确认并提交；若是 `AGENT_LOOP` 控制状态但没有 human request，汇报 loop reason、evidence 和 artifact 路径，等待用户决定。
- 完成后按 vendor run artifact 查询流程读取 summary 和 changed files，再结合目标 workflow 的 `AGENTS.md` 汇总结果、变更文件、阻塞项和下一步路由建议。

## Self Improve 触发与产出

`self-improve/` 是本 facade 的自我提升工作台，只保存发布包内的 schema、baseline eval、模板和只读脚本。运行期历史、报告、proposal 和本地 override 必须写入 `.local/`，不要放入发布包基线。

触发规则：

- 用户显式输入 `/lgwf-wf-agent self-improve`、`/lgwf-wf-agent 自我优化`，或自然语言要求复盘、自我优化、优化交互体验、沉淀 case、生成 proposal、生成 eval case 时，必须进入 self-improve 路由，而不是普通 workflow 派发。
- 只读类 self-improve 可直接执行：`eval`、`workflow-health`、`scorecard`、`changed-files`、`pre-release`。执行后报告产物路径和是否通过。
- 记录类 self-improve 需要确认：`incident`、`proposal`、`eval-case`。如果用户已经明确要求“记录这次问题/生成 proposal/生成 eval 草稿”，可以把当前对话作为证据直接执行；否则先展示拟记录摘要并等待确认。
- proposal 后续处理必须是两段式：先提醒用户是否查看或执行 proposal，再通过 `/lgwf-wf-agent 优化方案` 展示 review 计划；不直接执行 proposal，执行前必须先展示 review 计划并等待明确批准。
- 发布包变更类 self-improve 必须人工批准：`promote-eval`、修改 `SKILL.md`、`AGENTS.md`、`registry.json`、baseline eval 或 workflow 文件。
- 用户主动要求复盘、沉淀 case、生成 proposal 或运行 self eval 时，可以使用 `self-improve/scripts/*`。
- 修改 `SKILL.md`、`AGENTS.md`、`registry.json`、`workflows/*/AGENTS.md`、`workflows/**/workflow.lgwf`、`scripts/init_lgwf_wf_agent.py`、`scripts/doctor_lgwf_wf_agent.py`、`scripts/validate_registry.py`、`scripts/list_workflows.py` 或 vendor manifest 后，应运行 `python self-improve/scripts/run_self_evals.py`。
- 真实运行中出现路由错误、approval 处理错误、监控 handle 丢失、旧 `work_dir` 处理错误或最终报告缺口时，主 agent 只能建议记录 incident；必须用户确认后才能调用 `record_incident.py`。
- 发布前运行 `self_improve.py pre-release`；该 gate 必须覆盖 doctor、self eval、override 检查、workflow health、scorecard 和 upgrade report。

固定产出：

- `.local/self-improve/incidents/*.json`：用户确认后的真实问题记录。
- `.local/self-improve/reports/*self-eval.json` 和 `.md`：确定性 self eval 结果。
- `.local/self-improve/proposals/*.md`：基于 incident 或 eval report 生成的可审查改进提案。
- `.local/self-improve/scorecards/*.md`：周期复盘指标。
- `.local/overrides/AGENTS.local.md` 和 `.local/overrides/*.json`：本地私有 override，仅允许补充或收紧规则。

发布保护：

- 发布包可以覆盖 `self-improve/` 下的模板、schema 和 baseline eval。
- 发布包不得覆盖或删除 `.local/self-improve/`、`.local/overrides/` 或 `.local/upgrade-reports/`。
- 本地 override 不能绕过 approval、vendor client、路径安全、UTF-8、单 skill facade 或固定 workflow 路由约束。
- JSON override 必须符合 `self-improve/overrides/schema.json`；只允许 `additional_rules`、`local_work_dirs` 和 `experimental_workflows` 三类补充项。
- 本地 override 禁止替换核心 workflow id、绕过 approval、fallback 到外部 skill、覆盖 vendor 指引或放宽发布保护。
- 第一版不自动合并 override；如果 override 与新版发布文件冲突，只报告风险并等待人工处理。
- self-improve 脚本只生成记录、报告和 proposal，不自动修改 `AGENTS.md`、`registry.json`、workflow 文件或 vendor 文件。

第二版命令：

```powershell
python self-improve\scripts\run_self_evals.py
python self-improve\scripts\run_self_evals.py --changed-files <changed-files.json> --check-overrides
python self-improve\scripts\write_upgrade_report.py --version <version> --source <source>
python self-improve\scripts\record_incident.py --type routing --summary "..." --evidence-json "[...]"
python self-improve\scripts\create_proposal.py --incident <incident.json>
python self-improve\scripts\collect_changed_files.py --output .local\self-improve\changed-files.json
python self-improve\scripts\create_eval_case.py --incident <incident.json>
python self-improve\scripts\generate_scorecard.py
python self-improve\scripts\pre_release_check.py --version <version> --source <source>
python self-improve\scripts\promote_eval_case.py --draft <draft.json> --approved-by <user>
python self-improve\scripts\self_improve.py eval --check-overrides
python self-improve\scripts\self_improve.py pre-release --version <version> --source <source>
python self-improve\scripts\self_improve.py pre-release --version <version> --source <source> --run-workflow-tests
python self-improve\scripts\self_improve.py workflow-health
python self-improve\scripts\self_improve.py workflow-health --workflow-id wf-fix
python self-improve\scripts\self_improve.py workflow-tests --workflow-id wf-fix
python self-improve\scripts\self_improve.py workflow-proposal --workflow-id <id> --health-report <report.json> --incident <incident.json> --eval-report <eval.json> --changed-files <changed-files.json>
python self-improve\scripts\validate_manifest.py
```

`changed-files.json` 是相对 facade root 的字符串数组。命中 `SKILL.md`、`AGENTS.md`、`registry.json`、`workflows/*/AGENTS.md`、`workflows/**/workflow.lgwf`、`scripts/init_lgwf_wf_agent.py`、`scripts/doctor_lgwf_wf_agent.py`、`scripts/validate_registry.py`、`scripts/list_workflows.py` 或 vendor manifest 时，self eval report 必须记录触发原因。

`create_eval_case.py` 生成的是 `.local/self-improve/eval-case-drafts/` 下的草稿，不能自动进入 `self-improve/evals/`。只有人工审查确认后，才能把草稿提升为发布包 baseline eval。

`pre_release_check.py` 是发布前聚合入口；默认顺序是 `doctor` -> `collect_changed_files` -> `run_self_evals` -> `workflow_health` -> `generate_scorecard` -> `write_upgrade_report`。任一步失败时不得宣称发布检查通过。`promote_eval_case.py` 必须传入 `--approved-by`，用于记录人工批准者。

第五版以后，`self-improve/manifest.json` 是 self-improve 命令索引和发布保护策略的机器可读来源。新增、删除或重命名 self-improve 脚本时，必须同步更新 manifest，并运行 `validate_manifest.py`。

第六版以后，`self-improve/workflow-health/` 是内部 workflow 健康检查基线。`check_workflow_health.py` 只做确定性检查，包括 registry 路径、workflow `AGENTS.md`、内部 workflow 不含 `SKILL.md`、`work_dir` 不等于源码根和测试目录存在性。发现问题只能生成 report 或 `workflow-proposal`，不能自动修改内部 workflow。

第七版以后，workflow health 还会检查每个内部 workflow 的 `AGENTS.md` 是否明确写清四类语义边界：不负责什么、何时需要 approval、固定输出或产物在哪里、失败或不适用时如何回到 facade 路由。该检查只判断必要说明是否存在，不替代人工审查。

内部 workflow 自身测试默认不在 pre-release 中执行；需要发布前强验证时，显式运行 `self_improve.py workflow-tests` 或给 `self_improve.py pre-release` 增加 `--run-workflow-tests`。该步骤只执行 baseline 中的 `test_command`，不会运行目标业务 workflow。

`workflow-proposal` 可以合并 health report、incident、eval report 和 changed files，生成包含问题证据、影响范围、推荐修改文件、验收命令和是否需要用户 approval 的改进提案。`scorecard` 会统计最近 incident 类型、重复失败 workflow、路由误判次数和 approval 卡点次数，用于判断下一轮优先优化方向。

## 各 Workflow 输入摘要

`wf-fix` 启动时使用空 JSON object：

```json
{}
```

它会在第一个 approval 中询问 `target_workflow_lgwf`、`max_attempts` 和 `ask_main_agent_for_target_approvals`，随后再收集目标 workflow 自己的业务输入。

`wf-prompt-fix` 推荐输入：

```json
{
  "prompt_fix_target": {
    "target_workflow_lgwf": "D:/example/workflow.lgwf",
    "target_package_root": "D:/example",
    "target_dirs": ["D:/example"]
  }
}
```

`wf-prompt-upgrade` 推荐输入：

```json
{
  "prompt_upgrade_target": {
    "target_workflow_lgwf": "D:/example/workflow.lgwf",
    "target_package_root": "D:/example",
    "target_dirs": ["D:/example"]
  }
}
```

`e2e-test-generator` 会通过入口 approval 收集目标信息，目标 JSON 形态为：

```json
{
  "workflow_lgwf": "D:/example/workflow.lgwf",
  "workflow_root": "D:/example",
  "test_output_dir": "tests",
  "test_name_prefix": "example_workflow"
}
```

`plan` 推荐输入：

```json
{
  "react_task_request": {
    "objective": "要完成的复杂任务目标",
    "target_type": "modify_artifact",
    "analysis_target_files": ["D:/example/path/to/file.md"],
    "constraints": ["先生成计划和验收契约，用户确认后再修改目标文件"]
  }
}
```

最终以对应 workflow `AGENTS.md` 的输入契约为准。

## 更新 Bundled Client

1. 将新的 `lgwf-client-assist.zip` 临时复制到 `assets/lgwf-client-assist.zip`。
2. 执行 `python scripts/init_lgwf_wf_agent.py`。
3. 确认 `vendor/lgwf-client-assist/.lgwf-client-assist-vendor.json` 记录了新的 `zip_sha256`，且 `assets/lgwf-client-assist.zip` 已被删除。
4. 提交 `vendor/lgwf-client-assist/` 的实际内容变更；不要提交 zip 包。

## 最小验证

```powershell
Get-ChildItem -LiteralPath plugins\team-skills\skills\lgwf-wf-agent -Recurse -Filter SKILL.md
```

该命令应只返回根目录 `SKILL.md`。
