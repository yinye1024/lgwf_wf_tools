# lgwf-e2e-test-generator

`lgwf-e2e-test-generator` 用于为任意目标 LGWF workflow 生成一组固定职责的端到端测试脚本。

## 目标

输入一个目标 workflow package 后，本工作流会先分析目标 workflow 的结构，再固定生成四类测试：

- `script_flow_e2e`：脚本级全分支测试，不启动目标 workflow runtime。
- `runtime_fake_e2e`：启动真实 LGWF runtime，但使用 Python fake Codex 固定输出。
- `real_positive_e2e`：真实 Codex 正向业务闭环测试，作为人工验收入口；文件名不使用 `test_` 前缀，默认不纳入 `unittest discover` 回归集合。
- `wf_fix_positive_e2e`：复用真实正向场景启动 `wf-fix`，用于人工验收边跑边修复闭环；文件名不使用 `test_` 前缀，默认不纳入 `unittest discover` 回归集合。

## 输入

入口 approval 接收 JSON object：

```json
{
  "workflow_root": "D:/path/to/target-workflow",
  "workflow_lgwf": "D:/path/to/target-workflow/workflow.lgwf",
  "test_output_dir": "tests",
  "test_name_prefix": "target_workflow",
  "test_types": ["runtime_fake", "wf_fix_positive"]
}
```

`workflow_lgwf` 必填；其余字段可由工作流推导默认值。`test_types` 可省略或为空数组，默认生成全部四类；可选值为 `script_flow`、`runtime_fake`、`real_positive`、`wf_fix_positive`。

## 输出

目标 workflow 的测试目录下固定生成：

```text
test_<workflow>_script_flow_e2e.py
test_<workflow>_runtime_fake_e2e.py
lgwf_<workflow>_real_positive_e2e.py
lgwf_<workflow>_real_positive_e2e_for_wf_fix.py
```

真实 Codex 正向入口和 wf-fix 正向入口都不依赖环境变量开关；人工直接执行对应文件时才运行真实链路。wf-fix 正向入口的目标仍是原始 `workflow.lgwf`，不会把 Python 脚本当成 `target_workflow_lgwf`。

如果入口 `test_types` 只选择部分类型，未选中的生成阶段会被跳过，最终报告中显示为 `skipped`。

工作流运行目录中会生成中间产物：

```text
.lgwf/e2e_target_request.normalized.json
.lgwf/e2e_workflow_sources.json
.lgwf/e2e_workflow_graph.json
.lgwf/e2e_coverage_matrix.json
.lgwf/e2e_*_design.json
.lgwf/e2e_*_generation.json
.lgwf/e2e_*_observe.json
reports/e2e-test-generator/report.json
reports/e2e-test-generator/report.md
```

## 验证

```powershell
$lgwfPy = "skills\lgwf-wf-tools\vendor\lgwf-client-assist\scripts\lgwf.py"
python $lgwfPy audit skills\lgwf-wf-tools\workflows\e2e-test-generator\workflow.lgwf
python -m unittest discover skills\lgwf-wf-tools\workflows\e2e-test-generator\tests
```
