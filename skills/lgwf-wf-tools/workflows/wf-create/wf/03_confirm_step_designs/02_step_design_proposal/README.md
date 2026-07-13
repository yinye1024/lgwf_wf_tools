# step_design_proposal

## 职责

基于已确认业务流、脚手架计划、DSL 规范、模块化创建指引和模块契约生成完整结构化步骤设计草案，并在进入人工确认前通过小 ReAct 执行 proposal 质量闸和最多 3 轮修正。

## 输入

- `.lgwf/business_flow.json`
- `.lgwf/create_requirements.json`
- `.lgwf/scaffold_package_result.json`
- `.lgwf/step_design_proposal_react_context.json`
- `.lgwf/create_reference_context/step-design-reference-index.md`
- `.lgwf/create_reference_context/` 中由索引按需路由的 DSL、模块化和模块契约参考资料

## 输出

- `.lgwf/step_designs_proposal.json`
- `.lgwf/step_designs_proposal_quality_gate.json`
- `.lgwf/step_designs_proposal_decision.json`
- `.lgwf/step_design_proposal_react_context.json`

## 产物

`.lgwf/step_designs_proposal.json` 仍是确认前草案；只有 `03_step_design_review` 批准后才固化为 `.lgwf/step_designs.json`。步骤设计必须完整内联在 JSON 字段中，不再生成 `docs/steps/*.md`。

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
