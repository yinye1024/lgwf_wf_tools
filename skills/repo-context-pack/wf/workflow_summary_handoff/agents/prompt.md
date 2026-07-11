# 运行摘要与交接收尾

## 定位

本阶段属于 `repo-context-pack` 第一层子 workflow，职责是：校验上下文包产物，写出 workflow 运行摘要和交接报告。

## 输入输出

- 输入状态来自 `ws/.lgwf/` 下的上游 JSON。
- 输出写入 `.lgwf/repo_context_pack_summary.json`。
- 不修改 `target_dir` 内源码，不向 package 根目录写入运行态文件。

## 验收

- 阶段脚本可用 Python 标准库执行。
- 输出 JSON 为 UTF-8 no BOM。
- 阶段资源路径保持包内相对路径。
