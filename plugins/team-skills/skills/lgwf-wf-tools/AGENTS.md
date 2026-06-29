# LGWF Workflow Tools 指引

本目录是 LGWF workflow 工具集合的 facade 入口。主智能体只通过根目录 `SKILL.md` 与用户交互，再根据用户目标、目标 workflow 状态和 `registry.json` 派发到 `workflows/*` 下的内部 workflow package。

本 facade 的职责是三件事：

- 根据用户需求路由到合适的内部 workflow。
- 监控被派发 workflow 的执行，处理 approval、阻塞、失败诊断和收尾汇总。
- 根据真实执行暴露的问题进入 self-improve，沉淀证据并产出可审查改进。

本 facade 不默认负责“组装多个 workflow”或连续串联多个会修改目标 package 的 workflow。某个 workflow 完成后，如果结果证据显示需要进入另一个 workflow，应重新列出候选、说明理由并重新路由。

## 可用 Workflow

| Workflow id | 入口 | 主要职责 | 典型使用时机 |
| --- | --- | --- | --- |
| `wf-fix` | `workflows/wf-fix/wf/workflow.lgwf` | 运行目标 LGWF workflow，观察失败、阻塞或输出不满足契约的原因，在候选目录中修复并验证后 promote。 | 用户要“修复当前 workflow 失败”“跑起来并自愈”“根据真实失败改 DSL/prompt/script”。 |
| `wf-create` | `workflows/wf-create/wf/workflow.lgwf` | 根据用户原始意图创建新的 LGWF workflow 初稿，分阶段确认需求、业务流、步骤设计和实现初稿。 | 用户要“从零创建 workflow”“只有原始想法，帮我生成 workflow 初稿”“先确认需求和步骤设计再落目录”。 |
| `wf-prompt-fix` | `workflows/wf-prompt-fix/wf/workflow.lgwf` | 盘点目标 workflow 引用的 prompt，审计并修复基础规范、引用、上下文和输出契约问题。 | 用户要“检查 prompt 是否合格”“修复 prompt 引用/格式/输出契约”“交付前做 prompt acceptance”。 |
| `wf-prompt-upgrade` | `workflows/wf-prompt-upgrade/wf/workflow.lgwf` | 分析 prompt 的职责边界、上下游契约、质量指标和失败模式，生成升级方案并在用户确认后应用。 | 用户要“提升 prompt 质量”“优化 Agent 职责/决策标准/验收指标”“做 prompt 设计升级”。 |
| `e2e-test-generator` | `workflows/e2e-test-generator/workflow.lgwf` | 为已有目标 workflow 生成脚本级、runtime fake 和真实 Codex 正向三类 E2E 测试。 | 用户要“补 E2E 测试”“交付前建立回归入口”“为 workflow 生成测试骨架”。 |
| `plan` | `workflows/plan/wf/workflow.lgwf` | 把复杂任务拆成可确认的计划契约、验收契约，并在用户确认后按 ReAct 闭环执行。 | 用户要“先规划再执行”“先给验收标准”“按计划闭环实现复杂任务”“需要人工确认计划/验收后再改文件”。 |

实际路径、固定 `work_dir` 和对应 `AGENTS.md` 必须以根目录 `registry.json` 为准；不要硬编码已记忆的路径。

除 `/lgwf-wf-tools help` 或纯帮助请求外，路由前必须先列出可用 workflow。标准入口是 `python scripts/list_workflows.py`；如果已经从 `registry.json` 读取了同等清单，也必须向用户展示可用 workflow，并说明为什么选择目标 workflow。

## 路由规则

进入任何内部 workflow 路由前，先执行或等价展示 `scripts/list_workflows.py` 的清单。随后结合用户目标、目标路径、已有运行产物和错误证据，选择一个最合适的 workflow。

方案优先是普通目标路由的强制门槛。普通目标如果会修改目标 package、启动真实 workflow 或提交 approval，必须先说明：目标 workflow、输入来源、是否会修改文件、是否会真实运行、approval 边界和最小验证方式。未经用户明确确认，不得启动任何内部 workflow；用户明确说“立即运行”“直接修复”“自动执行”或给出等价授权时，可以直接启动。

`ambiguous_modify_goal` 是严格 proposal gate：当用户说“修复优化”“优化修复”“完善”“处理”“整理”“质量提升”等范围词，并同时给出目标目录、目标 workflow 或 package 路径时，一律先判定为 `ambiguous_modify_goal`。除非用户明确说“直接修改”或给出等价授权，否则只能做只读检查并输出 proposal；禁止改文件，禁止启动任何内部 workflow，禁止启动目标 workflow run。proposal 必须包含：目标、发现依据、候选路由、修改范围、是否真实运行、approval 边界、最小验证方式和明确的 will-not-do。

用户提出模糊的“优化/修复”目标时，不默认组装多个 workflow，也不默认连续执行质量链路。先按 `ambiguous_modify_goal` 输出 proposal；如果后续执行结果证据显示需要进入另一个 workflow，再重新列出候选、说明理由并重新路由。

优先根据用户的直接目标路由：

- 目标是运行失败、卡住、产物不对、需要自动诊断修复：使用 `wf-fix`。
- 目标是从原始意图创建新的 LGWF workflow 初稿：使用 `wf-create`。
- 目标是 prompt 文件缺失、引用不清、输入输出契约不完整、上下文约束不足：使用 `wf-prompt-fix`。
- 目标是 prompt 质量升级、角色职责重塑、评估标准、失败模式、上下游协作质量：使用 `wf-prompt-upgrade`。
- 目标是生成或刷新 workflow 的端到端测试：使用 `e2e-test-generator`。
- 目标是复杂任务规划、先产出计划/验收契约、用户确认后再按 ReAct 闭环执行：使用 `plan`。

再按证据修正路由：

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
- `assets/lgwf-client-assist.zip` 只作为临时同步输入；执行 `scripts/init_lgwf_wf_tools.py` 后必须记录 hash、解压到 `vendor/lgwf-client-assist/`、删除内部 `SKILL.md`，并删除该 zip。
- 不要把 `.lgwf/`、`ws/`、`ws_*`、`.tmp/`、`__pycache__/` 或 `assets/install-state.*` 当作源码。
- 如果固定 `work_dir` 已有历史 LGWF 数据，先按 continue/resume/rerun 流程询问用户，不要直接启动第二个 run。
- workflow package 内部 `SCRIPT`、`PROMPT`、`PROMPT_REF`、`CONTEXT workflow` 和 `STEP ... WORKFLOW` 路径必须保持相对路径；禁止绝对路径、`..` 和循环引用。
- 中文、复杂 JSON、approval value 和报告必须保持 UTF-8；在 PowerShell 中不要把包含中文的 JSON 直接塞进长命令文本，优先使用 UTF-8 文件或安全 argv 传参。

## 显式命令

- `/lgwf-wf-tools`：执行入口预检；如果 doctor 通过，继续理解用户目标；如果 doctor 失败且存在 `assets/lgwf-client-assist.zip`，自动运行 init 后再次 doctor；如果仍失败，停止并报告。
- `/lgwf-wf-tools help` 或 `/lgwf-wf-tools 帮助`：只展示帮助，不修改文件，不派发内部 workflow，不启动 LGWF run，不运行会写 `.local/` 的 self-improve 命令；帮助内容必须包含“可用指令”。
- `/lgwf-wf-tools init`：只运行 `python scripts/init_lgwf_wf_tools.py`，输出初始化报告；不派发内部 workflow。
- `/lgwf-wf-tools doctor`：只运行 `python scripts/doctor_lgwf_wf_tools.py`，输出只读健康检查报告；不修改文件，不派发内部 workflow。需要完整审计时运行 `python scripts/doctor_lgwf_wf_tools.py --deep`。
- `/lgwf-wf-tools list`：只运行 `python scripts/list_workflows.py`，只读列出 `registry.json` 中可派发的内部 workflow；不派发内部 workflow。
- `/lgwf-wf-tools self-improve`、`/lgwf-wf-tools 自我优化`、用户说“复盘这个 facade”“优化交互体验”“把这次问题沉淀成 case”：进入 self-improve 路由。

`commands.json` 是对外指令的机器可读清单。维护显式命令时必须同步更新 `commands.json`，并运行 `python scripts/complete_commands.py "<prefix>"` 验证补齐输出。

## Facade 初始化

初始化分三层处理，不放在内部 workflow node 里：

1. Doctor 预检层：处理任何 `/lgwf-wf-tools` facade 请求前，先运行 `python scripts/doctor_lgwf_wf_tools.py`。该脚本只读检查根 `SKILL.md`、`registry.json`、registry 路径、vendor `AGENTS.md`、`scripts/lgwf.py`、bundled wheel，以及 vendor 内不得存在 `SKILL.md`。
2. Init 同步层：doctor 失败且存在 `assets/lgwf-client-assist.zip` 时，自动运行 `python scripts/init_lgwf_wf_tools.py`。它负责从临时 zip 刷新 `vendor/lgwf-client-assist/`、删除内部 `SKILL.md`、清理 install-state、写入 `.lgwf-client-assist-vendor.json`，删除 zip，并把初始化报告写入 `.local/init/last-init.json`。init 后必须再次运行 doctor。
3. 派发前预检层：doctor 通过后，准备派发内部 workflow 前再读取 `registry.json` 和目标 workflow `AGENTS.md`；缺失时直接报告 facade 安装不完整，不 fallback 到外部 skill。
4. Runtime 安装层：LGWF wheel 的安装由 `vendor/lgwf-client-assist/scripts/lgwf.py` 在 `run`、`audit`、`status`、`approval`、`runs` 等命令需要 runtime/client 模块时按 bundled wheel 自动处理。`doctor` 只诊断，不安装。

不要新增“初始化 workflow”来安装 wheel。内部 workflow 启动本身就依赖 `lgwf.py run` 和 bundled wheel；把安装放进 workflow node 会让安装发生得太晚。

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

## 监控循环

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

## Self Improve

`self-improve/` 是本 facade 的自我提升工作台，只保存发布包内的 schema、baseline eval、模板和只读脚本。运行期历史、报告、proposal 和本地 override 必须写入 `.local/`，不要放入发布包基线。

触发规则：

- 用户显式输入 `/lgwf-wf-tools self-improve`、`/lgwf-wf-tools 自我优化`，或自然语言要求复盘、自我优化、优化交互体验、沉淀 case、生成 proposal、生成 eval case 时，必须进入 self-improve 路由；先归类问题、列出可执行的 self-improve 路径，再说明哪些操作需要用户确认。
- 真实运行中出现路由错误、approval 处理错误、监控 handle 丢失、旧 `work_dir` 处理错误或最终报告缺口时，主 agent 只能建议记录 incident；必须用户确认后才能调用 `record_incident.py`。
- 只读类 self-improve 可直接执行：`eval`、`workflow-health`、`scorecard`、`changed-files`、`pre-release`。
- 记录类 self-improve 需要确认：`incident`、`proposal`、`eval-case`。如果用户已经明确要求“记录这次问题/生成 proposal/生成 eval 草稿”，可以把当前对话作为证据直接执行。
- proposal 后续处理必须是两段式：先提醒用户是否查看或执行 proposal，再通过 `/lgwf-wf-tools 优化方案` 展示 review 计划；不直接执行 proposal，执行前必须先展示 review 计划并等待明确批准。
- 发布包变更类 self-improve 必须人工批准：`promote-eval`、修改 `SKILL.md`、`AGENTS.md`、`registry.json`、baseline eval 或 workflow 文件。
- 修改 `SKILL.md`、`AGENTS.md`、`registry.json`、`workflows/*/AGENTS.md`、`workflows/**/workflow.lgwf`、`scripts/init_lgwf_wf_tools.py`、`scripts/doctor_lgwf_wf_tools.py`、`scripts/validate_registry.py`、`scripts/list_workflows.py` 或 vendor manifest 后，应运行 `python self-improve/scripts/run_self_evals.py`。
- self-improve 脚本只生成记录、报告和 proposal，不自动修改 `AGENTS.md`、`registry.json`、workflow 文件或 vendor 文件。

固定产出：

- `.local/self-improve/incidents/*.json`：用户确认后的真实问题记录。
- `.local/self-improve/reports/*self-eval.json` 和 `.md`：确定性 self eval 结果。
- `.local/self-improve/proposals/*.md`：基于 incident 或 eval report 生成的可审查改进提案。
- `.local/self-improve/scorecards/*.md`：周期复盘指标。
- `.local/overrides/AGENTS.local.md` 和 `.local/overrides/*.json`：本地私有 override，仅允许补充或收紧规则。

发布包不得覆盖或删除 `.local/self-improve/`、`.local/overrides/` 或 `.local/upgrade-reports/`。

常用命令：

```powershell
python self-improve\scripts\run_self_evals.py
python self-improve\scripts\run_self_evals.py --changed-files <changed-files.json> --check-overrides
python self-improve\scripts\self_improve.py eval --check-overrides
python self-improve\scripts\self_improve.py workflow-health
python self-improve\scripts\self_improve.py workflow-tests --workflow-id wf-fix
python self-improve\scripts\self_improve.py pre-release --version <version> --source <source>
python self-improve\scripts\validate_manifest.py
```

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

`wf-create` 推荐输入：

```json
{
  "raw_intent": "要创建的新 LGWF workflow 原始意图"
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
2. 执行 `python scripts/init_lgwf_wf_tools.py`。
3. 确认 `vendor/lgwf-client-assist/.lgwf-client-assist-vendor.json` 记录了新的 `zip_sha256`，且 `assets/lgwf-client-assist.zip` 已被删除。
4. 提交 `vendor/lgwf-client-assist/` 的实际内容变更；不要提交 zip 包。

## 最小验证

```powershell
Get-ChildItem -LiteralPath plugins\team-skills\skills\lgwf-wf-tools -Recurse -Filter SKILL.md
```

该命令应只返回根目录 `SKILL.md`。
