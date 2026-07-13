# step_design_proposal

## 职责

基于已确认需求、已确认业务流、脚手架计划、DSL 规范、模块化创建指引和模块契约生成完整结构化步骤设计草案，并在进入人工确认前通过小 ReAct 执行 proposal 质量闸和最多 3 轮修正。ReAct 的 `REASON`、`ACT`、`OBSERVE`、`DECIDE` 都是独立 slot workflow，避免把分析、生成、审计和路由混在同一个 Codex 节点里。

## 输入

- `.lgwf/business_flow.json`
- `.lgwf/create_requirements.json`
- `.lgwf/scaffold_package_result.json`
- `.lgwf/step_design_observation.json`
- `.lgwf/create_reference_context/step-design-reference-index.md`
- `.lgwf/create_reference_context/` 中由索引按需路由的 DSL、模块化和模块契约参考资料

## 输出

- `.lgwf/step_design_reason.json`
- `.lgwf/step_designs_proposal.json`
- `.lgwf/step_design_structural_gate.json`
- `.lgwf/step_design_semantic_observation.json`
- `.lgwf/step_design_observation.json`
- `.lgwf/step_design_decision_analysis.json`
- `.lgwf/step_designs_proposal_quality_gate.json`
- `.lgwf/step_designs_proposal_decision.json`

## 产物

`.lgwf/step_designs_proposal.json` 仍是确认前草案；只有 `03_step_design_review` 批准后才固化为 `.lgwf/step_designs.json`。步骤设计必须完整内联在 JSON 字段中，不再生成 `docs/steps/*.md`。

`OBSERVE` slot 会先运行 deterministic structural gate，再由 Codex 做 semantic audit，最后合并为 `.lgwf/step_design_observation.json`。下一轮 `REASON` 只从 `step_design_observation.reason_feedback` 提取修复方向，再写出 `.lgwf/step_design_reason.json` 给 `ACT` 执行。`.lgwf/step_designs_proposal_quality_gate.json` 仅保留为最终 assert 的兼容入口，不作为新的分析契约。

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
- 不把 `.lgwf/step_designs_proposal_quality_gate.json` 当作下一轮 reason 的主反馈；主反馈只看 `.lgwf/step_design_observation.json`。
