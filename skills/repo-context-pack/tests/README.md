# repo-context-pack tests

本目录包含两类最小验证：

- `test_build_context_pack.py` 验证核心扫描脚本能生成固定上下文包产物。
- `test_workflow_structure.py` 验证内嵌 LGWF workflow 的目录边界、资源路径和入口契约。

运行方式：

```powershell
python -m unittest discover skills\repo-context-pack\tests
```
