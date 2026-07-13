# 设计测试与验收约束

## 步骤标识

- `step_slug`: `design-tests-and-acceptance`
- 对齐阶段：`04_workflow_summary_handoff`

## 目标

定义最小测试入口、固定产物验收规则和通过标准，确保 `repo-context-pack` 的首版实现以确定性校验而不是人工解释作为 `passed=true` 的依据。

## 输入

- 七个固定产物的存在性与解析要求
- 阶段交接 JSON 与汇总 JSON 的关键字段要求
- `target_dir` 只读、`output_dir` 可写、`ws/.lgwf/` 为状态边界

## 输出

- `tests/test_build_context_pack.py`
- `README.md` 中的最小验证命令
- `AGENTS.md` 中的边界与禁止事项
- `ws/.lgwf/repo_context_pack_summary.json`

## 确认要点

- 最小单测覆盖非法输入、固定产物存在性、JSON 可解析、摘要参数回写和状态边界
- `README.md` 或 `AGENTS.md` 必须记录 `lgwf.py audit`、`unittest` 和 `compileall` 的验证命令，但这些命令不在当前节点执行
- `repo_context_pack_summary.json` 的 `passed=true` 必须依赖固定产物和关键字段校验，不依赖人工解释

## 实现建议

- `tests/test_build_context_pack.py` 至少覆盖缺失 `target_dir`、输出目录不可写、JSON 解析失败、固定产物缺失和越界写入
- 将 `summary.json` 与 `repo_context_pack_summary.json` 的关键字段对齐，便于摘要阶段做确定性汇总
- 在文档中使用相对命令示例，例如 `<lgwf-client-assist>/lgwf.py audit wf/workflow.lgwf --work-dir ws`、`python -m unittest discover tests`、`python -m compileall scripts wf`
- 对 compileall、audit 和 unittest 的失败输出约定清晰失败语义，不把失败结果压成警告

## 验收

- 最小测试入口可以覆盖固定产物存在性、JSON 解析和状态边界
- `repo_context_pack_summary.json` 至少回写 `passed`、固定产物校验结果、扫描参数摘要和风险数量
- 文档中的验证命令全部为相对路径示例，不包含绝对路径或宿主机器特有信息

## 禁止事项

- 不要把人工主观判断写成 `passed=true` 的唯一依据
- 不要为了通过测试而放宽固定产物、编码或状态边界要求
- 不要在当前实现节点直接执行 audit、unittest 或 compileall 作为“生成文件”的一部分
