# 02_target_context_inventory 资源说明

本阶段资源目录当前只保留说明文档，不承载额外静态样例或模板。阶段运行逻辑完全由 [`scripts/run.py`](../scripts/run.py) 的确定性 Python 扫描实现。

## 阶段职责

- 接收上一阶段输出的 `repo_context_pack_request.json`
- 在只读边界内清点目标目录和目标文件
- 生成供 `03_context_pack_rendering` 使用的 `context_inventory.json`

## 资源边界

- 不在本目录放置运行时状态文件；状态仍写入工作区 `.lgwf/`
- 不缓存目标仓库源码副本
- 不保存需要人工维护的命令白名单；命令提取使用脚本内的固定启发式规则

## 验收关注点

- `workflow.lgwf` 只编排本阶段脚本，不再嵌套孙级 workflow
- `scripts/run.py` 只做确定性扫描与 JSON 渲染，不执行目标资料中的任何命令
- 产物固定为 `.lgwf/context_inventory.json`
