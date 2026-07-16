# step_design_proposal

## 职责

基于已确认需求、已确认业务流、脚手架计划、schema 和动态步骤设计契约生成完整结构化步骤设计草案。首轮先由 `build_step_design_contract` 同时生成动态校验契约和 bounded Codex 输入，随后由 `generate_step_designs` Codex 节点生成 step、directory 和 file 三级设计。

生成后，`normalize_step_designs_proposal` 只做机械规范化，例如路径、数组字段、owner/kind 推断和非法源码字段清理；它不生成 fallback workflow、通用 prompt 或通用脚本/JSON/Markdown/测试 contract。缺失或空泛设计必须由 `validate_step_designs_structure.py` 暴露并进入修复 ReAct。
normalize 不负责补齐缺失设计；所有 required file、stage workflow、target 引用和 coverage 缺口都必须由 structural gate 暴露，并由 repair plan/ACT 写回 proposal。

初检通过时直接进入最终 assert；初检失败时进入最多 2 轮修复 ReAct。修复 ReAct 仍按现有范式分工：`REASON CODEX` 读取 Python observation/decision 并生成详细修复方案，`ACT CODEX` 执行修复方案并重写 proposal，`OBSERVE PY` 做确定性验收，`DECIDE PY` 决定 `exit` 或 `continue`。

## 输入

- `.lgwf/business_flow.json`
- `.lgwf/create_requirements.json`
- `.lgwf/scaffold_package_result.json`
- `.lgwf/step_design_validation_contract.json`
- `.lgwf/step_design_authoring_context.json`
- `.lgwf/create_reference_context/step-design-reference-index.md`
- `.lgwf/create_reference_context/`
- `resources/step_designs_proposal.schema.json`
- `resources/step_designs_passing_example.json`
- 修复轮次内的 `.lgwf/step_design_observation.json`
- 修复轮次内的 `.lgwf/step_designs_proposal_decision.json`

## 输出

- `.lgwf/step_design_validation_contract.json`
- `.lgwf/step_design_authoring_context.json`
- `.lgwf/step_designs_proposal.json`
- `.lgwf/step_design_normalization_report.json`
- `.lgwf/step_design_repair_plan.json`
- `.lgwf/step_design_structural_gate.json`
- `.lgwf/step_design_observation.json`
- `.lgwf/step_design_decision_analysis.json`
- `.lgwf/step_designs_proposal_decision.json`

## 产物

`.lgwf/step_designs_proposal.json` 是 structural gate 的输入；只有 `03_step_design_review` 确认 observation 通过且 `proposal_hash` 匹配后才固化为 `.lgwf/step_designs.json`。步骤设计必须完整内联在 JSON 字段中，不再生成 `docs/steps/*.md`。04 实现阶段只消费 `.lgwf/step_designs.json`，不会再从 `.lgwf/scaffold_package_result.json` 补齐目标文件或目录。

proposal 包含三层设计：

- `directory_designs[]`：说明目标目录的定位、owner step、预期文件和禁止事项。
- `file_designs[]`：说明目标文件的类型、职责、结构轮廓、读写契约、依赖、验收说明和禁止事项；workflow/prompt 使用 `exact_content`，脚本、文档、JSON contract 和测试文件使用结构化 contract。
- `step_designs[]`：说明每个业务 step 的目标、输入、输出、依赖、实现建议、验收说明、确认点、目标文件、目标目录、运行产物和来源引用。

proposal 必须覆盖基础 package 文件：`AGENTS.md`、`README.md`、`entry_contract.json`、`wf/workflow.lgwf` 和 `wf/artifact_contracts.json`；同时必须覆盖每个 `wf/<stage>/artifact_contracts.json`，使 stage workflow 单独 audit 时具备 bootstrap/final 边界说明。这些文件也必须出现在某个 `step_designs[].target_files[]` 中。

## 验证

```powershell
python -m unittest discover skills\lgwf-wf-tools\workflows\wf-create\tests
```

## 禁止事项

- 不写入 `.lgwf/step_designs.json`。
- 不处理 `approve`、`revise`、`reject` 决策。
- `.lgwf/create_reference_context` 只作为 DSL/module 写作规则参考，首轮设计必须优先读取 `step-design-reference-index.md`，不得把参考目录当作业务输入或目标源码来源。
- 不读取 `04_implement_steps_react`、测试目录、目标 package 源码或仓库其他源码来推导步骤设计。
- 不读取入口参考资料路径或 `.lgwf/business_flow_proposal.json`；步骤设计只从已确认需求、已确认业务流和 scaffold plan 推导。
- 不设计与已确认脚手架计划冲突的目录结构。
- 不输出 Python 或测试源码字段；步骤设计必须给出 workflow/prompt 的 exact 内容，以及脚本、Markdown、JSON 的接口合同和验收要求。
- 不新增单独的 quality gate 反馈文件；主反馈只看 `.lgwf/step_design_observation.json`。
