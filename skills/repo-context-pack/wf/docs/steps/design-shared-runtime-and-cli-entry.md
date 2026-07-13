# 设计共享运行时与 CLI 入口

## 步骤标识

- `step_slug`: `design-shared-runtime-and-cli-entry`
- 对齐阶段：`01_entry_scope_resolution`、`02_target_context_inventory`、`03_context_pack_rendering`、`04_workflow_summary_handoff`

## 目标

提供一套确定性 Python 共享运行时，统一驱动 CLI 入口和四个阶段脚本，负责请求归一化、目录扫描、命令抽取、风险提炼、渲染落盘和结果汇总，不引入运行时 Codex prompt 扫描目标仓库。

## 输入

- `entry_contract.json` 约定的请求字段与默认值
- 固定阶段交接文件：`repo_context_pack_request.json`、`context_inventory.json`、`context_pack_generation.json`、`repo_context_pack_summary.json`
- `target_dir`、`output_dir`、包含/排除模式、截断阈值等扫描参数

## 输出

- `scripts/build_context_pack.py`
- `wf/shared/scripts/repo_context_runtime.py`

## 依赖

- 根契约文档中定义的只读/可写边界
- 阶段 workflow 约定的输入输出文件名
- 渲染契约定义的七个固定产物和汇总 JSON

## 确认要点

- CLI 入口与四个阶段脚本调用同一套共享运行时，不维护双实现
- 目标目录扫描、命令抽取、风险提炼和渲染全部由确定性 Python 完成
- 共享运行时统一约束 `target_dir` 只读、`output_dir` 可写、`ws/.lgwf/` 为状态边界

## 实现建议

- 将共享运行时拆成请求验证、路径规范化、扫描、渲染、摘要校验五类纯 Python 能力
- 阶段脚本只负责装配当前阶段输入输出，不复制扫描或渲染算法
- 为扫描结果保留截断状态、跳过原因、入口识别结果和命令来源，供渲染和摘要复用
- 把命令、TODO、修复步骤都当作仓库事实记录，不在运行时执行

## 验收

- 任何阶段都不需要运行时 Codex prompt 读取目标仓库
- CLI 和阶段脚本对非法输入、边界越界、不可读目录和不可写输出目录给出一致失败结果
- 阶段脚本对共享运行时的调用不形成额外状态目录，也不向目标 package 根写 `.lgwf`

## 禁止事项

- 不要为 CLI 和阶段脚本分别实现不同的扫描或渲染逻辑
- 不要在共享运行时中执行从目标资料抽取到的 shell、PowerShell、Python 或测试命令
- 不要把宿主仓库绝对路径写入渲染产物或状态 JSON
