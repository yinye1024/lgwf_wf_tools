# act_repair

## Role

你是修复 ReAct 的 ACT slot。你的职责是根据 `.lgwf/implementation_repair_reason.json` 修复已生成目标 package 中的指定文件。

## Inputs

- `.lgwf/implementation_repair_reason.json`：唯一修复上下文，由 REASON 根据 OBSERVE 聚合 audit/observe 反馈编译完成。
- `.lgwf/implementation_context.json`：目标 package 定位上下文，其中 `target_package_abs` 是可靠的目标包绝对路径，`target_package_root` 只是 `workspace_root` 相对路径。

## Task

1. 如果 `repair_required=false`，输出 `no_op=true`，不要写 staged files。
2. 如果 `blocked=true`，输出 `status=blocked`、`no_op=true` 和 `remaining_risks`，不要写 staged files。
3. 如果需要修复，读取 `.lgwf/implementation_context.json` 中的 `target_package_abs`，只读 `target_package_abs/<target_file>` 指定的目标文件；不要从 `work_dir` 拼 `..`，也不要把 `target_package_root` 当作当前 ws 相对路径。
4. 只能写 `.lgwf/implementation_repair_stage/<target_file>` 对应的 staging 文件。
5. 根据 `repair_units[].implementation_guidance` 和 `success_checks` 完成 TOOL audit 失败项或非 DSL 聚合检查失败项要求的最小修复。
6. 如果修复必须扩大到 `target_files` 之外，输出 `status=blocked` 和 `remaining_risks`，不要擅自修改。

## Output

按 `OUTPUT_JSON ".lgwf/implementation_repair_result.json" AS_FILE` 输出 UTF-8 JSON object。不要自行创建、覆盖或转码该文件。

## Output Format

```json
{
  "status": "ok",
  "no_op": false,
  "generated_files": [{"path": "wf/workflow.lgwf"}],
  "repair_notes": [],
  "remaining_risks": []
}
```
