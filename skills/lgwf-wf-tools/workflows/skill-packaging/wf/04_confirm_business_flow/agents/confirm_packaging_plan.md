# 打包计划确认

请只做二元审批：

- `approve`：接受当前打包计划和状态边界
- `reject`：计划不通过，当前 workflow 终止

必检项：

- `wf/workflow.lgwf` 为唯一入口
- 四个第一层阶段完整
- 运行状态只写入 `ws/.lgwf`
- 稳定动作脚本化，不由 Agent 直接自由落盘
