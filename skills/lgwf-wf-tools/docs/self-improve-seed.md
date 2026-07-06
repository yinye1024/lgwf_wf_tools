# Self Improve Seed

本文用于把 `workflows/self-improve/` 中的通用模式实例化到任意目标 workflow package。生成后的目标 workflow 拥有自己的 `self-improve/` 目录和 `.local/self-improve/` 运行期目录，不依赖 `lgwf-wf-tools` 的 self-improve 脚本。

## 适用条件

- 用户要求“把 self-improve 功能加到这个 workflow 上”。
- 用户要求目标 workflow 具备类似 self-improve 的 incident、proposal、eval、trace-eval、check 和 scorecard 能力。
- 用户明确要求目标 workflow 自包含，不依赖 `lgwf-wf-tools`。

## 执行方式

```powershell
python workflows/self-improve-seed/scripts/seed_self_improve.py --target <workflow-package>
```

目标路径可以是：

- 包含 `wf/workflow.lgwf` 的 workflow package 目录。
- 包含 `workflow.lgwf` 的 workflow 目录。
- 直接指向 `workflow.lgwf` 文件。

为 `lgwf-wf-tools` 内部已注册 LGWF workflow 批量铺设时，范围以 `registry.json` 中 `kind=lgwf` 的 entry 为准。已经存在 `self-improve/` 的目标默认跳过并单独运行检查；只有确认要重建发布包基线时才使用 `--force`，且不得删除目标 `.local/self-improve/` 运行历史。

## 生成结构

```text
<target>/
  self-improve/
    AGENTS.md
    README.md
    manifest.json
    evals/baseline-cases.json
    trace-eval/
      workflow.json
      golden_cases/runtime_trace_contract/
        case.json
        spec.json
        golden_trace.json
    templates/proposal.template.md
    scripts/
      self_improve.py
      record_incident.py
      create_proposal.py
      generate_scorecard.py
      run_self_evals.py
      run_trace_eval.py
      check_self_improve.py
      _paths.py
  .local/self-improve/
```

## 生成后的常用命令

```powershell
python self-improve\scripts\self_improve.py eval
python self-improve\scripts\self_improve.py trace-eval
python self-improve\scripts\self_improve.py check
python self-improve\scripts\self_improve.py scorecard
python self-improve\scripts\self_improve.py proposal --incident <incident.json>
```

`trace-eval` 会编译并运行目标 `workflow.lgwf`，把 `trace.json`、`eval-suite.json` 和摘要写入 `.local/self-improve/reports/`。第一版只做 runtime smoke，不内置业务 golden case；目标 workflow 后续可以自行收紧 `self-improve/trace-eval/golden_cases/` 下的 spec。

`check` 会串联 `eval`、`trace-eval` 和 `scorecard`。生成脚本对每个步骤设置默认超时，避免复杂 workflow 在空输入或人工节点上长期挂起；如果超时，报告会保留失败证据，后续应由目标 workflow 自己收紧 trace-eval 输入或说明限制。

## 边界

- 默认不覆盖已有 `self-improve/`；需要重建时显式传 `--force`。
- `--force` 只重建目标 `self-improve/` 发布包文件，不应覆盖或清理 `.local/self-improve/`。
- 生成脚本只依赖 Python 标准库、目标 workflow 自身目录，以及当前 Python 环境中可用的 `lgwf_dsl` 和 `lgwf_client`。
- 生成器不修改目标 `workflow.lgwf` 的业务节点；目标 workflow 何时调用自己的 self-improve，由目标 workflow 后续设计决定。
- 生成器只提供自我提升结构和命令入口，不自动应用 proposal。
