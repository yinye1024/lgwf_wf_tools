# skill-packaging self-improve 指引

## 模块类型

- `tool_workflow`

## 模块定位

本目录是 `skill-packaging` 本地自检入口，只服务当前 workflow package 的入口、契约和验证基线检查。

## 入口

- `manifest.json`
- `scripts/self_improve.py`
- `scripts/check_self_improve.py`

## 依赖

- 只依赖当前 workflow package 内的 `AGENTS.md`、`README.md`、`entry_contract.json`、`wf/workflow.lgwf` 和 `tests/`。

## 状态边界

- 本地运行报告写入 `.local/self-improve/`。
- 不读写 facade 级 self-improve 状态。

## 产物

- `.local/self-improve/check-latest.json`

## 验证

```powershell
python self-improve\scripts\self_improve.py check
```

## 禁止事项

- 不调用 facade 级 self-improve。
- 不修改 registry、workflow 源码或打包产物。
