# 产物读取规则

workflow 完成后必须读取 summary、changed files 和目标 workflow 约定产物，再汇总：

- 最终状态。
- 关键产物。
- 变更文件。
- 阻塞项。
- 下一步路由建议。

运行期产物优先写入目标 workflow 的 `ws/`、`.lgwf/` 或 facade 根目录 `.local/`，不得混入发布包基线目录。
