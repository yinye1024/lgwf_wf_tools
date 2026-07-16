# 步骤设计阶段

## 职责

本阶段负责把已确认业务流、脚手架计划和模块化规则转换为结构化步骤设计 JSON。步骤设计通过 structural gate 和 repair ReAct 收敛后自动固化 `.lgwf/step_designs.json`，再生成实现阶段使用的 `.lgwf/implementation_context.json`。

## 输入

- `.lgwf/business_flow.json`
- `.lgwf/create_requirements.json`
- `.lgwf/scaffold_package_result.json`

## 输出

- `.lgwf/create_reference_context/*`
- `.lgwf/step_designs_proposal.json`
- `.lgwf/step_design_repair_plan.json`
- `.lgwf/step_design_structural_gate.json`
- `.lgwf/step_design_observation.json`
- `.lgwf/step_design_decision_analysis.json`
- `.lgwf/step_designs_proposal_decision.json`
- `.lgwf/step_designs.json`
- `.lgwf/implementation_context.json`

## 子流程

- `01_reference_context`：复制 DSL、模块化开发和模块契约参考资料，发布 `.lgwf/create_reference_context/step-design-reference-index.md` 和 `.lgwf/create_reference_context/implementation-reference-index.md` 两个索引；scaffold 结构信息来自 `.lgwf/scaffold_package_result.json`。
- `02_step_design_proposal`：先由 `build_step_design_contract.py` 准备 `.lgwf/step_design_validation_contract.json` 和 `.lgwf/step_design_authoring_context.json`，再由 `generate_step_designs` Codex 节点读取 `.lgwf/create_reference_context/step-design-reference-index.md` 和 `.lgwf/create_reference_context/` 中的 DSL/module 参考资料，生成完整 step、directory 和 file 三级 `.lgwf/step_designs_proposal.json`；随后由 Python normalize 和 structural gate 初检。若存在问题，进入 `REASON CODEX / ACT CODEX / OBSERVE PY / DECIDE PY` 修复 ReAct，`REASON` 生成 `.lgwf/step_design_repair_plan.json`，`ACT` 通过 `EDIT_FILE` 直接编辑 `.lgwf/step_designs_proposal.json`，`OBSERVE` 运行 `validate_step_designs_structure.py` 发布 `.lgwf/step_design_observation.json`，`DECIDE` 将失败反馈写回下一轮。
- `03_step_design_review`：确认当前 proposal 已通过 structural gate 且 `proposal_hash` 未过期，随后自动固化步骤设计并准备实现上下文。

## 状态边界

本阶段只读写当前 run 的 workspace 产物，运行状态仍由 `wf-create/ws/.lgwf/` 承载。父 workflow 只编排子流程，不读取子流程内部私有脚本或 prompt 作为隐式接口。步骤设计的业务事实只来自已确认需求、已确认业务流和 scaffold plan；`.lgwf/create_reference_context` 只作为 DSL/module 写作规则参考，不作为业务输入或目标源码来源。

## 验证

```powershell
python -m unittest discover skills\lgwf-wf-tools\workflows\wf-create\tests
```

## 禁止事项

- 不直接生成目标 workflow 实现文件。
- 不绕过 structural gate 写入 `.lgwf/step_designs.json`。
- 不在 observation 的 `proposal_hash` 与当前 proposal 不一致时固化步骤设计。
- 不读取 `04_implement_steps_react`、测试目录或目标 package 源码来反推步骤设计。
