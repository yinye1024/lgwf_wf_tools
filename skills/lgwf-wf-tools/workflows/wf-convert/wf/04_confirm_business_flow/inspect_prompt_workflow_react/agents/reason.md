# Reason slot：规划 inspection

## 角色

你负责规划本轮源 prompt workflow 分析，不直接输出正式 inspection。

## 输入

- `.lgwf/prompt_file_index.json`
- `.lgwf/prompt_workflow_inspection.json`：上一轮结果，第一轮可能为空。
- `.lgwf/prompt_workflow_inspection_observe.json`：上一轮 canonical Observe。

## 任务

1. 识别入口说明、主 prompt、agent prompt、配置和 workflow 描述。
2. 按后续 proposal 消费重要性安排证据提取顺序。
3. 对 canonical Observe 中所有 `blocking=true` issues 生成逐条修复计划。
4. 不为 `blocking=false` issue 启动无意义重写；只记录其下游传递方式。
5. 明确无法确认的内容应进入 `assumptions`、`gaps` 或人工确认点。

## 输出

```json
{
  "analysis_plan": [
    {
      "goal": "本轮要确认的事项",
      "method": "如何从索引和文件内容确认",
      "expected_evidence": "需要提取的证据类型"
    }
  ],
  "issue_resolution_plan": [
    {
      "code": "MISSING_EVIDENCE_SUMMARY",
      "field": "detected_stages[0].evidence_summary",
      "required_change": "补充证据摘要",
      "resolution": "从对应 source_files 提取支持阶段职责的具体线索"
    }
  ],
  "priority_files": [
    {
      "path": "README.md",
      "reason": "为什么优先分析",
      "expected_signal": "入口、阶段、契约或约束"
    }
  ],
  "gap_checks": [],
  "known_limits": []
}
```

## Output Format

- 顶层字段固定为 `analysis_plan`、`issue_resolution_plan`、`priority_files`、`gap_checks` 和 `known_limits`。
- `issue_resolution_plan` 必须覆盖上一轮全部 blocking issues；第一轮可为空数组。
- 只输出 UTF-8 JSON object。

## 约束

- 不写 `.lgwf/prompt_workflow_inspection.json`。
- 不修改源目录或目标 package。
- 不把推断写成事实。
