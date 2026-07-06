# 测试说明

当前最小测试只验证 `wf-audit-fix` 初稿的结构契约：

- 根目录不生成可运行 `workflow.lgwf`
- `wf/` 是唯一 workflow root
- 四个第一层 stage workflow 存在
- 每个 stage 目录具备 `agents/`、`scripts/`、`resources/`

它不承诺业务 happy path，也不替代运行期 `audit`。
