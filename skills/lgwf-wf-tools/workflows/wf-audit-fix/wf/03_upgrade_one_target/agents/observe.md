# OBSERVE PY 复检说明

当前 workflow 的 observe slot 使用 `OBSERVE PY`，不调用 Codex prompt。实际复检由 `scripts/observe_repair.py` 执行。

`observe_repair.py` 的职责：

- 复跑当前目标 `.lgwf` 的 audit check。
- 写入 `.lgwf/current_target_audit.json`。
- 写入 `.lgwf/repair_observation.json`，记录 changed、diagnostic_count、diagnostic_delta 和 diagnostic identities。
- 把 audit check 的 diagnostics 返回给后续 `DECIDE PY`，由 decide 控制继续或退出。
