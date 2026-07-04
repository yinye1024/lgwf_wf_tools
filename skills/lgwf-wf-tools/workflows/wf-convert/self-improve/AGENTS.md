# wf-convert Self Improve

本目录为目标 workflow 的自包含自我提升模块。它依赖当前 workflow package、Python 标准库，以及当前 Python 环境可用的 `lgwf_dsl` / `lgwf_client`。

## 使用边界

- 真实问题经用户确认后，使用 `incident` 记录。
- proposal 只生成可审查提案，不自动修改 workflow。
- `trace-eval` 在 `wf-convert` 中执行非交互 compile smoke，基于编译结果生成报告；完整转换流程包含人工确认、子 workflow 和 handoff，不应在自优化检查中用空输入启动。
- `.local/self-improve/` 是运行期历史，发布或复制模板时必须保留用户已有历史。
