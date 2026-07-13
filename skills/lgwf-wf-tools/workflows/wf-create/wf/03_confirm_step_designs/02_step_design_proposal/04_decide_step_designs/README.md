# decide_step_designs

## 职责

本 slot workflow 先由 Codex 解释当前 observation 是否可退出，再由 Python 脚本写入 `.lgwf/step_designs_proposal_decision.json` 和顶层 `next` route。

## 输入

- `.lgwf/step_design_observation.json`
- `.lgwf/step_designs_proposal.json`

## 输出

- `.lgwf/step_design_decision_analysis.json`
- `.lgwf/step_designs_proposal_decision.json`

## 产物

`step_design_decision_analysis.json` 只供解释；`step_designs_proposal_decision.json` 是 ReAct 兼容 route 决策记录。

## 验证

```powershell
python -m unittest skills\lgwf-wf-tools\workflows\wf-create\tests\test_proposal_quality_gate.py
```

## 禁止事项

- Codex prompt 不写 `next`。
- Python 脚本不得让失败 observation 退出循环。
- 不写 `.lgwf/step_designs.json`。
