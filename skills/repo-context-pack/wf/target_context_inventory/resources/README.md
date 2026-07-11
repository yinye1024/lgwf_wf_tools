# 目标仓库上下文采集 resources

本目录保存 `target_context_inventory` 阶段的局部资源。第一版阶段逻辑集中在 `scripts/run.py`，共享稳定技术逻辑位于 `wf/shared/scripts/repo_context_runtime.py`。

禁止在本目录放置运行态 `.lgwf` 文件或目标仓库扫描结果。
