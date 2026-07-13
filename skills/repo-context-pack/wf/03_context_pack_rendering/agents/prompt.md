# `03_context_pack_rendering` Prompt 占位

本阶段首版默认不在运行时调用 Codex。

保留本文件是为了给后续人工接管或 prompt 化改造提供清晰边界；在当前设计里，`context pack` 的渲染、落盘和索引都必须由 `scripts/run.py` 的确定性 Python 逻辑完成。

## 阶段目标

- 读取 `.lgwf/context_inventory.json` 与 `.lgwf/repo_context_pack_request.json`。
- 生成 `.lgwf/context_pack_generation.json` 作为阶段交接产物。
- 在 `reports/repo-context-pack/` 下落盘 Markdown、JSON 和产物索引。

## 禁止事项

- 不得扫描目标仓库或重新读取业务源码目录。
- 不得把渲染逻辑迁移到运行时 Codex prompt。
- 不得写入 `reports/repo-context-pack/` 之外的任意运行产物目录。
- 不得引入绝对路径、盘符路径或 `..`。

## 如未来确需接入 Codex

- 只能消费本阶段上游已经整理好的 inventory / request 产物。
- 只能补充说明文字、报告组织或人工复核提示，不能替代 `scripts/run.py` 的确定性渲染。
- 任何新增 prompt 都必须继续保持 UTF-8 中文文档基线，并同步更新本阶段资源说明。
