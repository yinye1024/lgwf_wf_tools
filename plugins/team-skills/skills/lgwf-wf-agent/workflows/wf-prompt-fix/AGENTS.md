# LGWF Workflow Prompt Fix 指引

本目录是 `lgwf-wf-agent` facade 下的内部 workflow package，职责是盘点、验收并修复目标 LGWF workflow package 中被 `PROMPT` 或 `PROMPT_REF` 引用的 prompt 文件。它不是独立 Codex skill，不得单独注册；外部只能通过 `lgwf-wf-agent` 根目录 `SKILL.md` 和 `registry.json` 派发到本目录的 `wf/workflow.lgwf`。

## 业务职责

- 读取用户指定的目标 `workflow.lgwf`，确定目标 package root 和允许 Codex 审计、修复的目标目录。
- 扫描目标 workflow DSL，建立 prompt inventory，确认每个 prompt 引用的来源、用途和上下文。
- 审计 prompt 的基础规范问题，包括缺失文件、引用不清、输入输出契约不完整、上下文约束不足、职责边界含混等会影响 workflow 可维护性和运行稳定性的缺陷。
- 把审计结果交给用户选择：可以只生成验收摘要，也可以选择部分或全部 issue 进入自动修复。
- 对用户确认的 issue 执行最多 3 轮 `REACT` 修复循环：先生成修复方案，再应用到目标 prompt 文件，最后复核修复结果。
- 输出 prompt acceptance summary，并在需要时请求用户做最终确认。

本 workflow 只处理 prompt 基础验收和修复，不负责运行目标 workflow、不负责修复 Python script 或 LGWF runtime 失败，也不负责做 prompt 质量升级。如果根因是 workflow 执行失败，应由 facade 路由到 `wf-fix`；如果目标是提升 prompt 策略、角色设计、质量指标或复杂协作契约，应路由到 `wf-prompt-upgrade`。

## 适用场景

- 目标 workflow 准备交付，需要检查 prompt 引用、上下文文件和输出契约是否完整。
- workflow DSL 已能解析，但 prompt 文件存在基础规范问题，影响后续运行、测试生成或人工维护。
- 用户希望先获得 prompt audit summary，再决定哪些问题允许自动修复。
- 在执行 `wf-prompt-upgrade` 或 `e2e-test-generator` 前，需要先把 prompt 基础验收项清理到可用状态。

不适合的场景：

- 目标目录还没有可解析的 `workflow.lgwf`。
- 当前目标是修复 runtime、runner、script 或 DSL lowering 失败；应优先使用 `wf-fix`。
- 当前目标是重写 prompt 设计质量、拆分角色职责或建立高级评估标准；应优先使用 `wf-prompt-upgrade`。
- 用户要求直接运行目标 workflow 做业务验收；本 workflow 不启动目标 workflow runtime。

## 输入契约

启动时通过 `--input-json` 传入目标 workflow 信息，推荐格式为：

```json
{
  "prompt_fix_target": {
    "target_workflow_lgwf": "D:/example/workflow.lgwf",
    "target_package_root": "D:/example",
    "target_dirs": ["D:/example"]
  }
}
```

- `target_workflow_lgwf` 必填，可以是用户机器上的绝对路径。
- `target_package_root` 可省略，默认使用 `target_workflow_lgwf` 所在目录。
- `target_dirs` 可省略，默认使用 `target_package_root`；只应包含允许本 workflow 审计和修复的目标目录。
- workflow package 内部引用 `SCRIPT`、`PROMPT`、`PROMPT_REF` 和 `CONTEXT workflow` 时仍必须使用相对路径，不允许绝对路径或 `..`。

入口 `init_prompt_fix_target` 会先请求人工确认目标 JSON；确认后持久化到 work dir 的 `.lgwf/prompt_fix_target.json`，后续节点只读取该标准化目标信息。

## 业务流程

1. `init_prompt_fix_target`：请求用户确认目标 workflow 信息，并写入 `.lgwf/prompt_fix_target.json`。
2. `check_lgwf_client_assist`：确认 facade 内置 `lgwf-client-assist` 可用；只接受 bundled client 或测试显式注入的 client。
3. `build_prompt_inventory`：扫描目标 workflow DSL 和 prompt 引用，生成 `.lgwf/prompt_acceptance/inventory.json`。
4. `audit_target_prompts`：由 Codex 审计 prompt 文件、引用关系、上下文和输出契约，生成 `.lgwf/prompt_acceptance/audit.json`。
5. `prepare_prompt_fix_selection_context`：整理 audit summary 和可选 issue，准备人工选择上下文。
6. `select_prompt_fixes`：请求用户选择要修复的 issue；用户可以选择修复，也可以跳过修复直接汇总。
7. `validate_prompt_fix_selection` 和 `route_after_prompt_selection`：校验选择结果，并决定进入修复循环或直接生成摘要。
8. `repair_target_prompts`：对已确认 issue 执行最多 3 轮 `REACT` 修复，依次生成修复计划、应用修改、复核结果。
9. `summarize_prompt_acceptance`：汇总 inventory、audit、选择、修复和复核结果。
10. `route_after_prompt_acceptance_summary`：根据摘要状态决定自动结束或进入最终确认。
11. `confirm_prompt_acceptance` 或 `finish_prompt_acceptance`：记录用户最终确认，或在无需确认时完成 workflow。

进入 `waiting_human` 时，主 agent 必须展示 workflow 给出的 audit summary、issue 选项、修复风险或 acceptance summary，只提交用户明确确认的结果。不要绕过 approval，也不要直接修改 `.lgwf/` runtime artifacts。

## 固定输出

运行 work dir 中会保留这些主要产物：

```text
.lgwf/prompt_fix_target.json
.lgwf/prompt_acceptance/environment_check.json
.lgwf/prompt_acceptance/inventory.json
.lgwf/prompt_acceptance/audit.json
.lgwf/prompt_acceptance/fix_selection.json
.lgwf/prompt_acceptance/repair_plan.json
.lgwf/prompt_acceptance/repair_review.json
.lgwf/prompt_acceptance/react_history.json
.lgwf/prompt_acceptance/summary.json
.lgwf/prompt_acceptance/confirmation.json
```

其中 `repair_plan.json`、`repair_review.json` 和 `react_history.json` 只有在用户选择进入修复路径时才一定存在；如果用户跳过修复，最终摘要仍应说明未修复项和后续建议。

## 使用方式

本 workflow 应由 `lgwf-wf-agent` facade 派发：

1. 读取 facade 根目录 `registry.json` 中 `wf-prompt-fix` 的 `workflow_lgwf`、`work_dir` 和 `agents_md`。
2. 读取本文件，按输入契约准备 `--input-json`；涉及中文或复杂 JSON 时优先写入 UTF-8 文件再传递。
3. 使用 bundled client 启动并持续跟进同一个 run：

```powershell
$lgwfPy = "plugins\team-skills\skills\lgwf-wf-agent\vendor\lgwf-client-assist\scripts\lgwf.py"
python $lgwfPy run --workflow-lgwf plugins\team-skills\skills\lgwf-wf-agent\workflows\wf-prompt-fix\wf\workflow.lgwf --work-dir plugins\team-skills\skills\lgwf-wf-agent\workflows\wf-prompt-fix\ws --input-json <json> --background
python $lgwfPy status --session-id <session-id>
python $lgwfPy wait --session-id <session-id>
```

固定 `work_dir` 如果已有历史 LGWF 数据，先按 facade 的 continue/rerun 流程询问用户，不要直接启动第二个 run。跟进过程中使用 `status` 和 `wait` 持续追踪同一个 `lgwf_wf_prompt_fix` run。

缺少 bundled `lgwf-client-assist` 时必须直接失败并报告，不要 fallback 到用户 `.codex` 目录的外部 skill。workflow package 内的资源引用保持相对路径；用户提供的目标 workflow 路径可以是绝对路径。

## 本 package 自检

修改本 workflow package 后，至少执行：

```powershell
$lgwfPy = "plugins\team-skills\skills\lgwf-wf-agent\vendor\lgwf-client-assist\scripts\lgwf.py"
python $lgwfPy audit plugins\team-skills\skills\lgwf-wf-agent\workflows\wf-prompt-fix\wf\workflow.lgwf
python -m unittest discover plugins\team-skills\skills\lgwf-wf-agent\workflows\wf-prompt-fix\tests
```

如果只修改本说明文件，可以不运行完整 workflow，但应确认 UTF-8 内容可读、路径示例仍与当前目录结构一致。
