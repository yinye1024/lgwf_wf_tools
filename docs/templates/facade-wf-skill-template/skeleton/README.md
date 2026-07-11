# Facade Template

这是一个可复制的 facade workflow skill skeleton。它展示如何用 `SKILL.md`、`AGENTS.md`、`registry.json`、`entry_contract.json` 和共享规则目录组织内部 workflow。

## 模块类型

- `codex_skill`
- facade skill，内部 workflow 由 `registry.json` 管理。

## 入口

```text
/facade-template
/facade-template help
/facade-template list
/facade-template doctor
```

自然语言 workflow 请求进入 `AGENTS.md`，再由 `registry.json` 路由到内部 workflow。

## 依赖

- 目标仓库提供 Python。
- `kind=lgwf` 的 workflow 需要目标仓库提供 LGWF runtime，并通过 `--lgwf-py` 或 `LGWF_PY` 传给 `scripts/run_skill_workflow.py`。

## 状态与产物

- facade 本地状态写入 `.local/`。
- 示例 LGWF workflow 的状态写入 `workflows/example-workflow/ws/.lgwf/`。
- 示例 tool workflow 的输出由脚本参数决定。

## 验证

```powershell
python scripts\validate_registry.py
python scripts\list_workflows.py
python tests\test_registry_template.py -v
```

## 迁移提示

复制到真实仓库后，删除示例 workflow 或替换为真实 workflow。不要把 `example-workflow` 留在正式 registry 中。
