# wf-fix 自我提升模块

常用命令：

```powershell
python self-improve/scripts/self_improve.py eval
python self-improve/scripts/self_improve.py trace-eval
python self-improve/scripts/self_improve.py check
python self-improve/scripts/self_improve.py incident --type runtime --summary "..." --evidence-json "[]"
python self-improve/scripts/self_improve.py proposal --incident <incident.json>
python self-improve/scripts/self_improve.py scorecard
```

`eval` 检查自我提升结构；`trace-eval` 运行目标 workflow 并生成 `trace.json` / `eval-suite.json` evidence；`check` 串联二者并刷新 scorecard。

复杂 workflow 如果需要业务输入、人工确认或子 workflow，默认 `trace-eval` 可能失败或超时；这表示需要为本模块补充专门的 trace-eval 输入或 golden case，不表示可以绕过 `eval` 和结构检查。
