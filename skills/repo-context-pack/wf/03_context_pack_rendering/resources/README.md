# `03_context_pack_rendering` 资源说明

## 定位

本阶段负责把上游整理好的 `context inventory` 渲染成可交付的 `repo context pack` 产物，并输出给下游汇总阶段使用的交接 JSON。

## 输入

- workspace 文件：`.lgwf/context_inventory.json`
- workspace 文件：`.lgwf/repo_context_pack_request.json`

## 输出

- workspace 文件：`.lgwf/context_pack_generation.json`
- workspace 目录：`reports/repo-context-pack/`
- workspace 文件：
  - `reports/repo-context-pack/repo-context-pack.md`
  - `reports/repo-context-pack/repo-context-pack.json`
  - `reports/repo-context-pack/artifact-index.json`

## 运行边界

- 本阶段只做确定性 Python 渲染，不在运行时调用 Codex 分析目标仓库。
- 输出路径固定落在 workspace `reports/repo-context-pack/`，避免把运行产物写回 workflow package。
- 所有读写路径必须保持相对路径，不使用绝对路径、盘符路径或 `..`。
- 阶段脚本可以根据 request 补充说明信息，但首版不负责实现任意自定义输出目录映射。

## 最小验收

- `scripts/run.py` 能在 UTF-8 下读取输入 JSON，并写出 3 份渲染产物与 1 份阶段交接 JSON。
- `workflow.lgwf` 只包含本阶段单个 `PY` 节点，不向孙级 workflow 下沉。
- 产物索引中的路径与实际落盘文件一致。
