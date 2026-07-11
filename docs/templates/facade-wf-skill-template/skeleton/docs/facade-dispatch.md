# Facade 派发与监控

本文承载 workflow 启动、继续、监控、approval 和收尾规则。真实仓库应按自己的 runtime 补充细节。

## 派发执行

派发前由 `AGENTS.md` 完成目标选择。对于 registry 内的 LGWF workflow，使用：

```powershell
python scripts\run_skill_workflow.py --workflow-id <id> --input-json-file <input.json> --lgwf-py <path-to-lgwf.py>
```

如果目标仓库内置 runtime，可以把 `--lgwf-py` 改成固定路径，或设置环境变量：

```powershell
$env:LGWF_PY = "vendor/lgwf-client-assist/scripts/lgwf.py"
```

## 监控

启动后台 workflow 后必须保存 run handle，例如 `session_id`、`pid`、`work_dir` 或 runtime 返回的状态文件路径。后续 `status`、`wait`、`approval` 和收尾都围绕同一个 handle。

## Approval

`waiting_human` 不是完成状态。

- 如果是 approval 或 review，按 `workflows/01-share/approval.md` 展示确认模板。
- 只提交用户明确确认的决策。
- `approve` 是纯决策，不携带业务 JSON。
- 只有 `review revise` 需要提交完整业务 value。

## 收尾

完成后汇总：

- 最终状态。
- 关键产物。
- 变更文件。
- 阻塞项。
- 下一步路由建议。
