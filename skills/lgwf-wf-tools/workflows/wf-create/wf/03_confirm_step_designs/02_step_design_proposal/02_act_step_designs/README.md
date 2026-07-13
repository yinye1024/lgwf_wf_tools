# act_step_designs

## 职责

本 slot workflow 根据 `.lgwf/step_design_reason.json` 生成或修复 `.lgwf/step_designs_proposal.json`。

## 输入

- `.lgwf/step_design_reason.json`
- `.lgwf/business_flow.json`
- `.lgwf/create_requirements.json`
- `.lgwf/scaffold_package_result.json`
- `.lgwf/create_reference_context/step-design-reference-index.md`
- `.lgwf/create_reference_context/`

## 输出

- `.lgwf/step_designs_proposal.json`

## 产物

`step_designs_proposal.json` 是确认前草案，只能由后续 review 子流程批准后固化为 `.lgwf/step_designs.json`。

## 验证

```powershell
python -m unittest discover skills\lgwf-wf-tools\workflows\wf-create\tests
```

## 禁止事项

- 不写 `.lgwf/step_designs.json`。
- 不生成 Markdown 步骤设计草案。
- 不读取实现阶段、测试目录或目标 package 源码。
- 不扩大已确认需求、业务流和 scaffold plan 的范围。
