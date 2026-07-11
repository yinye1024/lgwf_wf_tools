# wf-dsl-upgrade 测试说明

本目录保存 `wf-dsl-upgrade` 的最小回归测试，覆盖以下边界：

- workflow 目录结构、自包含阶段目录与根编排引用。
- 共享 helper 的路径授权、audit 命令构造和诊断键归一化。
- `dry_run` / `apply` / `reject` 的关键升级路径。
- 升级后 diff 口径与 summary 状态映射。

运行命令：

```powershell
python -m unittest discover skills\lgwf-wf-tools\workflows\wf-dsl-upgrade\tests
```
