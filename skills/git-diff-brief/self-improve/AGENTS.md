# git-diff-brief Self Improve

本目录为目标 workflow 的自包含自我提升模块。它依赖当前 workflow package、Python 标准库，以及当前 Python 环境可用的 `lgwf_dsl` / `lgwf_client`。

## 使用边界

- 真实问题经用户确认后，使用 `incident` 记录。
- proposal 只生成可审查提案，不自动修改 workflow。
- `trace-eval` 在本 workflow 中执行静态 trace readiness（`audit` + `compile`），不自动启动完整摘要 runtime。
- 真实 runtime trace 应通过 `lgwf-wf-tools` 正常 rerun 获取，并作为 incident/proposal evidence 关联。
- `.local/self-improve/` 是运行期历史，发布或复制模板时必须保留用户已有历史。
