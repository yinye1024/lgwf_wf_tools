# reason_step_designs

## 职责

本 slot workflow 只把上一轮 `.lgwf/step_design_observation.json` 的 `reason_feedback` 编译成本轮 `.lgwf/step_design_reason.json`，供 ACT slot 生成或修复步骤设计 proposal。

## 输入

- `.lgwf/create_requirements.json`
- `.lgwf/business_flow.json`
- `.lgwf/scaffold_package_result.json`
- `.lgwf/step_design_observation.json`
- `.lgwf/step_designs_proposal_decision.json`
- `.lgwf/step_designs_proposal.json`

## 输出

- `.lgwf/step_design_reason.json`

## 产物

`step_design_reason.json` 是本轮 ACT 的操作指令，不是步骤设计 proposal，也不是确认后的 `.lgwf/step_designs.json`。

## 验证

```powershell
python -m unittest discover skills\lgwf-wf-tools\workflows\wf-create\tests
```

## 禁止事项

- 不生成 `.lgwf/step_designs_proposal.json`。
- 不写 `.lgwf/step_designs.json`。
- 不读取实现阶段、测试目录或目标 package 源码。
- 不重新设计已确认需求、业务流或 scaffold plan。
