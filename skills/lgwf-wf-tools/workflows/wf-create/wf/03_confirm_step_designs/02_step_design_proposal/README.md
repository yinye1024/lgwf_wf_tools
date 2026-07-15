# step_design_proposal

## 职责

基于已确认需求、已确认业务流、脚手架计划、schema、动态步骤设计契约和模块契约生成完整结构化步骤设计草案。首轮先由 `build_step_design_contract` 生成动态校验契约，再由 `generate_step_designs` Python 节点确定性生成 step、directory 和 file 三级设计，随后由 `normalize_step_designs_proposal` 对可机械修复的结构问题做确定性规范化，最后由 Python 执行初版结构校验；初检失败时进入最多 2 轮修复 ReAct。

初检通过时直接进入最终 assert；初检失败时才进入修复 ReAct。修复 ReAct 仍按现有范式分工：`REASON CODEX` 读取 Python observation/decision 并生成详细修复方案，`ACT CODEX` 执行修复方案并重写 proposal，`OBSERVE PY` 做确定性验收，`DECIDE PY` 决定 `exit` 或 `continue`，并在失败时把下一轮待修改信息写回给 REASON。

修复轮 `REASON CODEX` 和修复轮 `ACT CODEX` 必须使用同一个 `KEEP_SESSION KEY "design_codex"`，让诊断方案和修复执行共享同一个 Codex 逻辑 session。首轮 `generate_step_designs` 不使用 Codex，避免 skill 入口触发和参考资料过度读取影响稳定性。

## 输入

- `.lgwf/business_flow.json`
- `.lgwf/create_requirements.json`
- `.lgwf/scaffold_package_result.json`
- `.lgwf/step_design_validation_contract.json`
- `resources/step_designs_proposal.schema.json`
- `resources/step_designs_passing_example.json`
- 修复轮次内的 `.lgwf/step_design_observation.json`
- 修复轮次内的 `.lgwf/step_designs_proposal_decision.json`

## 输出

- `.lgwf/step_designs_proposal.json`
- `.lgwf/step_design_validation_contract.json`
- `.lgwf/step_design_normalization_report.json`
- `.lgwf/step_design_repair_plan.json`
- `.lgwf/step_design_structural_gate.json`
- `.lgwf/step_design_observation.json`
- `.lgwf/step_design_decision_analysis.json`
- `.lgwf/step_designs_proposal_decision.json`

## 产物

`.lgwf/step_designs_proposal.json` 仍是确认前草案；只有 `03_step_design_review` 批准后才固化为 `.lgwf/step_designs.json`。步骤设计必须完整内联在 JSON 字段中，不再生成 `docs/steps/*.md`。04 实现阶段只消费 `.lgwf/step_designs.json`，不会再从 `.lgwf/scaffold_package_result.json` 补齐目标文件或目录。

proposal 当前包含三层设计：

- `directory_designs[]`：说明目标目录的定位、owner step、预期文件和禁止事项。
- `file_designs[]`：说明目标文件的类型、职责、结构轮廓、读写契约、依赖、验收说明和禁止事项；每个文件必须声明 `content_mode`，workflow/prompt 使用 `exact_content`，脚本、文档、JSON contract 和测试文件使用结构化合同字段。
- `step_designs[]`：说明每个业务 step 的目标、输入、输出、依赖、实现建议、验收说明、确认点、目标文件、目标目录、运行产物和来源引用。

因此 proposal 必须覆盖基础 package 文件：`AGENTS.md`、`README.md`、`entry_contract.json`、`wf/workflow.lgwf` 和 `wf/artifact_contracts.json`；同时必须覆盖每个 `wf/<stage>/artifact_contracts.json`，使 stage workflow 单独 audit 时具备 bootstrap/final 边界说明。这些文件也必须出现在某个 `step_designs[].target_files[]` 中。

`build_step_design_contract` 从已确认业务流和 scaffold plan 提取 canonical stage id、stage alias、required stage workflow 和基础 required file design，写入 `.lgwf/step_design_validation_contract.json`。`generate_step_designs` 必须按该动态契约、静态 schema、通过示例和 scaffold `create_files` 输出 proposal；所有 scaffold 目标文件都要进入 `file_designs[]` 并被 `step_designs[].target_files[]` 引用。`normalize_step_designs_proposal` 会补齐缺失的基础 file design、阶段 workflow 覆盖、非空数组字段、路径格式和常见类型说明，但不会放宽质量门。

修复轮次中，`REASON CODEX` 只读取 observation、decision、动态 contract、schema 和通过示例，不再读取完整 structural gate，以免失败明细造成上下文膨胀。`ACT CODEX` 按 `.lgwf/step_design_repair_plan.json` 通过 `EDIT_FILE ".lgwf/step_designs_proposal.json"` 直接编辑当前 proposal，`OBSERVE PY` 每轮直接运行 `scripts/validate_step_designs_structure.py` 对当前 proposal 做确定性结构验收。

`file_designs` 不承载 Python 或测试源码；禁止使用 `content`、`full_source`、`source_code`、`code`、`body` 等字段输出完整文件内容。需要完整 LGWF DSL 或 prompt 时，只能使用白名单字段 `exact_content`，并由 structural gate 检查。

## 验证

```powershell
python -m unittest discover skills\lgwf-wf-tools\workflows\wf-create\tests
```

## 禁止事项

- 不写入 `.lgwf/step_designs.json`。
- 不处理 `approve`、`revise`、`reject` 决策。
- 不读取 `04_implement_steps_react`、测试目录、目标 package 源码或仓库其他源码来推导步骤设计。
- 不读取入口参考资料路径或 `.lgwf/business_flow_proposal.json`；步骤设计只从已确认需求、已确认业务流和 scaffold plan 推导。
- 不设计与已确认脚手架计划冲突的目录结构。
- 不输出 Python 或测试源码字段；步骤设计必须给出 workflow/prompt 的 exact 内容，以及脚本、Markdown、JSON 的接口合同和验收要求。
- 不新增单独的 quality gate 反馈文件；主反馈只看 `.lgwf/step_design_observation.json`。
