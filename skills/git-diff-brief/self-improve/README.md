# git-diff-brief 自我提升模块

常用命令：

```powershell
python self-improve/scripts/self_improve.py eval
python self-improve/scripts/self_improve.py trace-eval
python self-improve/scripts/self_improve.py check
python self-improve/scripts/self_improve.py incident --type runtime --summary "..." --evidence-json "[]"
python self-improve/scripts/self_improve.py proposal --incident <incident.json>
python self-improve/scripts/self_improve.py scorecard
```

`eval` 检查自我提升结构；`trace-eval` 在本 workflow 中执行静态 trace readiness（`audit` + `compile`），不会无人值守启动完整 `git-diff-brief` runtime；`check` 串联结构检查、trace readiness 和 scorecard。

`git-diff-brief` 的真实 runtime 包含人工 REVIEW 和 Codex 摘要节点。需要真实 trace 证据时，应通过 `lgwf-wf-tools` 正常 rerun，并把 `ws/.lgwf/runs/<run_id>/trace.json` 作为 incident/proposal evidence。
