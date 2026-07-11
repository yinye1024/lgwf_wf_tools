# tests

当前最小测试只覆盖 workflow package 自身的结构约束：

- 根目录没有可运行 `workflow.lgwf`
- 存在 `wf/workflow.lgwf`
- 六个第一层阶段目录自包含 `workflow.lgwf`、`agents/`、`scripts/`、`resources/`
- 不存在孙级 workflow
- `internal_workflow_package` 不生成根 `SKILL.md`
- 已批准的 `wf/docs/steps/*.md` 副本已经复制到目标 package

运行方式：

```powershell
python -m unittest discover skills\lgwf-wf-tools\workflows\skill-packaging\tests
```
