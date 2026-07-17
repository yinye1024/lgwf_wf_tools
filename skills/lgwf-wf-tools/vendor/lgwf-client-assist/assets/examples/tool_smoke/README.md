# Tool + Codex Smoke 示例

这个示例依次执行 `TOOL`、`CODEX` 和 `PY` 节点，演示当前推荐的 `.lgwf` authoring 方式和显式 `CONTRACT` 消费链。

authoring package 不包含任何 JSON 文件；runtime `workflow.json` 只会生成在独立 `work_dir/.lgwf/workflow/` snapshot 中。

```powershell
python <skill-dir>\scripts\lgwf.py run --workflow-lgwf <skill-dir>\assets\examples\tool_smoke\workflow.lgwf --work-dir <work_dir> --input-json "{}"
```

成功时，`output/message.md` 包含 `LGWF`、`TOOL` 和 `CODEX`，并通过最终 Python 验证节点。
