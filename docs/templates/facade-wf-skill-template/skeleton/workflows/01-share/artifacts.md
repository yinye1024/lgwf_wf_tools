# 产物规则

workflow 产物必须可定位、可解释、可验证。

## 通用要求

- 运行状态写入声明的状态目录。
- 用户需要查看的报告写入稳定路径。
- 跨阶段消费的内容必须固化为 artifact、report、handoff payload 或 state 字段。
- 不得让父 workflow 依赖子 workflow 的临时内部文件。

## 推荐命名

```text
<work_dir>/.lgwf/result_summary.json
<work_dir>/.lgwf/<workflow-id>_context.json
<work_dir>/reports/<workflow-id>/report.md
```

## 发布包排除

发布包默认排除：

- `.local/`
- `.lgwf/`
- `.test-output/`
- `__pycache__/`

生成物不应成为规范来源；规范应写在 `README.md`、`AGENTS.md`、`entry_contract.json` 或共享规则中。
