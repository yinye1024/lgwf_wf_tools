# wf-convert 自我提升模块

常用命令：

```powershell
python self-improve/scripts/self_improve.py eval
python self-improve/scripts/self_improve.py trace-eval
python self-improve/scripts/self_improve.py check
python self-improve/scripts/self_improve.py incident --type runtime --summary "..." --evidence-json "[]"
python self-improve/scripts/self_improve.py proposal --incident <incident.json>
python self-improve/scripts/self_improve.py scorecard
```

`eval` 检查自我提升结构；`trace-eval` 在 `wf-convert` 中执行非交互 compile smoke，并生成 `.local/self-improve/reports/latest-trace-eval.json`；`check` 串联二者并刷新 scorecard。

`wf-convert` 包含人工确认、子 workflow 和 handoff，完整运行验证应继续使用专门的端到端测试，不在自优化检查中用空输入启动完整转换流程。

复杂 workflow 如果需要业务输入、人工确认或子 workflow，默认 `trace-eval` 可能失败或超时；这表示需要为本模块补充专门的 trace-eval 输入或 golden case，不表示可以绕过 `eval` 和结构检查。
