# 设计上下文包渲染契约

## 步骤标识

- `step_slug`: `design-rendering-contracts`
- 对齐阶段：`03_context_pack_rendering`、`04_workflow_summary_handoff`

## 目标

固定上下文包渲染产物的文件名、职责、编码和排序规则，确保渲染结果可被后续 handoff、摘要校验和人工阅读稳定消费。

## 输入

- `.lgwf/context_inventory.json`
- `.lgwf/repo_context_pack_request.json`
- 输出目录、截断阈值、入口识别结果、模块映射和命令清单

## 输出

- `output_dir/repo_context_pack.md`
- `output_dir/agent_handoff.md`
- `output_dir/module_map.json`
- `output_dir/command_inventory.json`
- `output_dir/risk_register.md`
- `output_dir/read_order.md`
- `output_dir/summary.json`
- `ws/.lgwf/context_pack_generation.json`

## 固定产物职责

- `repo_context_pack.md`：面向阅读者的仓库上下文总览、入口、模块关系和关键风险
- `agent_handoff.md`：面向下游代理的执行摘要、阅读建议、边界和下一步
- `module_map.json`：模块、入口、依赖和主要文件的结构化映射
- `command_inventory.json`：从仓库资料抽取出的命令、来源文件、用途和风险标记
- `risk_register.md`：需要优先暴露的风险、边界、缺失项和截断说明
- `read_order.md`：建议阅读顺序，严格遵循入口文件、说明文件、核心模块、测试脚本、风险相关文件
- `summary.json`：固定产物完整性、扫描参数、统计摘要、截断状态和关键路径回写
- `context_pack_generation.json`：阶段级生成记录，供汇总阶段和确定性校验消费

## 确认要点

- 七个固定产物文件名与职责保持不变
- Markdown 产物使用中文说明；JSON 产物以 UTF-8 no BOM 编码并可解析
- 路径字段优先使用相对 `target_dir` 的路径，`summary.json` 与 `context_pack_generation.json` 都要显式暴露扫描参数与截断状态

## 实现建议

- 对被截断或跳过的目录、文件和命令分别记录原因，避免在渲染阶段吞掉事实
- 在 `read_order.md` 中将风险相关文件排在基础入口、说明文件、核心模块和测试脚本之后
- 在 `summary.json` 中回写固定产物存在性、JSON 解析结果、产物计数和目标目录摘要
- 在 `context_pack_generation.json` 中保留渲染开始/结束时间、输出目录、已写文件列表和警告项

## 验收

- 七个固定产物全部存在，且 `module_map.json`、`command_inventory.json`、`summary.json`、`context_pack_generation.json` 可成功解析
- Markdown 与 JSON 中不出现绝对路径、盘符路径或 `..`
- `read_order.md` 的顺序规则与本步骤文档一致

## 禁止事项

- 不要更改固定产物文件名
- 不要把未执行的 TODO、修复步骤或测试命令包装成“已完成动作”
- 不要在 `summary.json` 或 `context_pack_generation.json` 中省略扫描参数、截断状态或写入边界
