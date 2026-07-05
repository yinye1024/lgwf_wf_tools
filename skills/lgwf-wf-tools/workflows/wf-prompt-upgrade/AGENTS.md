# LGWF Workflow Prompt Upgrade

本目录是 `lgwf-wf-tools` facade 下的内部 workflow package，不是独立 Codex skill。它专门处理“目标 workflow 引用的 prompt 是否具备足够强的设计能力、上下游契约和质量控制”，并在用户确认后把升级方案应用到目标 workflow package。

## 模块契约

- 模块类型：`lgwf_workflow_package`。
- 执行前必须读取 `../01-share/module-contract.md`、`../01-share/registry-contract.md`、`../01-share/lgwf-dispatch.md`、`../01-share/lgwf-monitor.md`、`../01-share/approval.md` 和 `../01-share/artifacts.md`。
- prompt 升级不得扩大目标模块边界；入口、状态边界、产物和验证方式仍以目标模块自身契约为准。

本 workflow 不替代 `wf-prompt-fix`。`wf-prompt-fix` 负责基础规范、引用、输出格式和明显契约问题；本 workflow 负责更高一层的 prompt 设计升级，例如职责边界、角色能力、决策标准、失败模式、验收指标和可执行修改计划。默认推荐先运行 `wf-prompt-fix`，再运行 `wf-prompt-upgrade`。

## 业务目标

- 盘点目标 workflow 中通过 `PROMPT` / `PROMPT_REF` 引用的 prompt 文件。
- 分析每个 prompt 所在 node 的业务职责、输入上下文、输出 artifact、后续消费方和失败模式。
- 找出能实际提升 workflow 产出质量、稳定性或可验收性的升级机会。
- 生成结构化升级方案，先交给用户确认，不在确认前修改目标文件。
- 在用户 approve 后，只按确认范围修改目标 workflow package 内的相关 prompt/source 文件。
- 输出升级摘要，供主 agent 决定是否继续运行 prompt 验收、目标 workflow 或 E2E 测试生成。

## 输入契约

facade 必须根据根目录 `registry.json` 派发到 `wf/workflow.lgwf`，并使用 registry 中的相对 `work_dir`。启动时通过 `--input-json` 传入目标 workflow 信息：

```json
{
  "prompt_upgrade_target": {
    "target_workflow_lgwf": "D:/example/workflow.lgwf",
    "target_package_root": "D:/example",
    "target_dirs": ["D:/example"]
  }
}
```

`target_workflow_lgwf` 必填，表示要升级 prompt 的目标 workflow authoring source。`target_package_root` 可省略，默认由 workflow 根据目标文件推导。`target_dirs` 可省略，默认限制在目标 package root 内。

入口 `init_prompt_upgrade_target` 会先让主 agent 确认该 JSON，然后持久化为 `.lgwf/prompt_upgrade_target.json`。用户提供的目标 workflow 路径可以是绝对路径；workflow package 内的资源引用必须保持相对路径。

## 运行流程

根 `wf/workflow.lgwf` 只负责编排阶段，不直接展开每个脚本、prompt、approval 和 apply 节点。阶段细节由第一层子 workflow 承担：

1. `prepare_target`：确认目标 workflow 信息，检查 facade bundled `lgwf-client-assist` 是否可用，并盘点目标 package 内所有可发现 `workflow.lgwf` 引用的 prompt，生成 inventory。该盘点包括嵌套 workflow，但排除 `.lgwf`、`ws`、`reports`、`data` 等运行或产物目录。
2. `design_upgrade`：使用 ReAct 三段式生成升级设计。
   - `REASON` 分析现状和升级机会，写 `.lgwf/prompt_upgrade/analysis.json`。
   - `ACT` 生成升级方案，写 `.lgwf/prompt_upgrade/proposal.json`。
   - `OBSERVE` 复核方案质量，写 `.lgwf/prompt_upgrade/proposal_review.json`。
3. `confirm_upgrade`：把 proposal、review 和风险整理成人工确认上下文，向用户展示升级项、文件范围、质量指标、验收检查和风险，让用户批准全部、批准部分或拒绝，并校验用户决策。拒绝分支在本子流程内部通过 `FAIL_ALL` 终止整个 run，不把 route 决策暴露给根 workflow。
4. `apply_upgrade`：阶段内部先判断是否存在已批准升级项；没有已批准项时只写入跳过态 review 并返回，有批准项时再生成 apply plan。该阶段目录必须自包含，`ACT` prompt 和辅助脚本放在 `04_apply_upgrade/agents` 与 `04_apply_upgrade/scripts`，不得再拆出孙级 workflow；应用修改时只能处理 `.lgwf/prompt_upgrade/apply_plan.json` 中声明的文件和步骤。
5. `summary`：用于 apply 后或无可应用升级时输出 summary；用户明确拒绝时由 `FAIL_ALL` 终止，不再生成成功态 summary。

目录结构遵循两层 workflow 规则：第一层是 `wf/workflow.lgwf` 主编排；第二层是 `wf/<stage>/workflow.lgwf` 子工作流。子工作流目录必须自包含 prompt、spec、resources 和 stage-local scripts；不得在子工作流目录下再放 `*/workflow.lgwf`。

## 人工确认语义

`confirm_prompt_upgrade` 是本 workflow 的关键控制点。主 agent 必须向用户展示：

- prompt 数量、升级项数量和是否可以确认。
- proposal summary、目标结果和每个升级项的 `id`。
- 每个升级项涉及的 `prompt_path`、`node_id`、当前缺口、升级意图、计划修改、质量指标、验收检查和风险控制。
- `files_to_modify` 和整体 `risks`。
- 三种决策含义：
  - 批准全部：`{"approve": true, "approved_upgrade_ids": [], "reject": false}`。
  - 批准部分：`{"approve": true, "approved_upgrade_ids": ["..."], "reject": false}`。
  - 拒绝：`{"approve": false, "approved_upgrade_ids": [], "reject": true}`，会通过 `FAIL_ALL` 终止整个 run。

如果用户只说 `approve`，默认批准全部升级。用户明确拒绝时，由 `confirm_upgrade` 子流程内部通过 `FAIL_ALL` 终止整个 run，不进入 apply 或 summary。根 workflow 不读取 `.lgwf/prompt_upgrade/decision.json`，也不承接子流程返回的 route。

## 升级方案质量要求

升级项必须能追溯到具体 prompt、workflow node 和可执行修改。不要把“更清晰”“更完整”“更详细”作为独立目标；质量指标必须可观察、可验收、可拒绝。

每个候选升级需要按 `impact`、`confidence`、`user_value`、`implementation_cost` 和 `risk` 评分。通常只有 `impact >= 2`、`confidence >= 2`、`user_value >= 2` 且 `risk <= 2` 的候选进入 `prompt_upgrades[]`；证据不足或价值不明确的候选进入 `deferred_upgrades[]`。

`proposal.json` 至少应表达：

- `summary`
- `target_outcome`
- `prompt_upgrades[]`
- `files_to_modify[]`
- `quality_metrics[]`
- `acceptance_checks[]`
- `risks[]`
- `deferred_upgrades[]`

## 修改边界

- 设计阶段不得修改目标文件，只能写 `.lgwf/prompt_upgrade/*.json`。
- apply 阶段只能修改目标 workflow package 内、用户已批准升级涉及的文件。
- 不修改 `.lgwf/` runtime artifacts，除本 workflow 指定写入的 `.lgwf/prompt_upgrade/*.json` 和 `.lgwf/target_prompt_upgrade_summary.json`。
- 不擅自扩大升级范围；发现 proposal 与目标文件现状冲突时，停止对应升级项并写入 review。
- 默认不修改 `lgwf_wf_prompt_upgrade` 自身文件；只有当 `target_package_root` 明确指向本 workflow package，且用户确认该目标后，才允许把自身 prompt 当作目标处理。
- 不把基础规范问题伪装成设计升级；规范问题只作为背景风险记录，必要时建议回到 `wf-prompt-fix`。

## 主 agent 使用方法

1. 从 facade 根目录读取 `registry.json`，选择 `wf-prompt-upgrade` 的 `workflow_lgwf`、`work_dir` 和本 `AGENTS.md`。
2. 准备 `prompt_upgrade_target` 输入；涉及中文或复杂 JSON 时，优先写入 UTF-8 文件再传入。
3. 使用 bundled client 启动或继续同一个 run：

```powershell
python vendor\lgwf-client-assist\scripts\lgwf.py run --workflow-lgwf workflows\wf-prompt-upgrade\wf\workflow.lgwf --work-dir workflows\wf-prompt-upgrade\ws --input-json "<json>" --background
```

4. 使用同一个 `session_id` / `pid` / `work_dir` 通过 `status`、`wait`、`approval` 和 `runs` 持续推进。
5. 遇到 `waiting_human` 时按 `workflows/01-share/approval.md` 的人工确认展示模板展示 workflow 给出的 confirmation context，只提交用户明确确认的 JSON 决策。
6. 结束后汇总最终状态、关键产物、实际修改文件、未应用升级、剩余风险和建议下一步。

如果固定 `work_dir` 已有历史 LGWF 数据，按 facade 的 continue/rerun 规则处理，不要直接启动第二个 run。

## 输出产物

在固定 work dir 下查看这些产物：

- `.lgwf/prompt_upgrade_target.json`
- `.lgwf/prompt_upgrade/inventory.json`
- `.lgwf/prompt_upgrade/analysis.json`
- `.lgwf/prompt_upgrade/proposal.json`
- `.lgwf/prompt_upgrade/proposal_review.json`
- `.lgwf/prompt_upgrade/decision.json`
- `.lgwf/prompt_upgrade/apply_plan.json`
- `.lgwf/prompt_upgrade/apply_review.json`
- `.lgwf/prompt_upgrade/summary.json`
- `.lgwf/target_prompt_upgrade_summary.json`
