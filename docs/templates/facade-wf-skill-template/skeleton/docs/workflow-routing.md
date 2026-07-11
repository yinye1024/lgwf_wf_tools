# 内部 Workflow 路由

本文用于普通 workflow 任务的内部 workflow 选择。实际路径、固定 `work_dir` 和 `agents_md` 以根目录 `registry.json` 为准。

## 路由前置

进入内部 workflow 路由前，先列出可用 workflow：

```powershell
python scripts\list_workflows.py
```

随后读取 `registry.json`、目标 workflow 的 `entry_contract.json` 和目标 workflow 的 `AGENTS.md`，并说明为什么选择目标 workflow。

## Workflow 选择表

| Workflow id | 使用时机 |
| --- | --- |
| `example-workflow` | 需要演示或验证 LGWF runtime workflow 派发。 |
| `example-tool-workflow` | 需要演示或验证脚本型 workflow 派发。 |

## 输入和派发

准备输入时先读 registry 指向的 `entry_contract.json`，必要时查 [workflow-inputs.md](workflow-inputs.md)。内部 LGWF workflow 推荐通过代理脚本按 workflow id 启动：

```powershell
python scripts\run_skill_workflow.py --workflow-id example-workflow --input-json-file input.json --lgwf-py <path-to-lgwf.py>
```

脚本会按 contract 自动补 `--workflow-lgwf`、`--work-dir`，并将 inline JSON 转为 UTF-8 输入文件。

## 连续路由

每个阶段只选择一个内部 workflow。不要默认组装多个 workflow；阶段结果需要继续处理时，再重新列出候选并说明理由。
