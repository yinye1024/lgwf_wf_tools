# lgwf-guide 测试

`lgwf-guide` 的回归测试统一放在 facade 根目录 `tests/test_lgwf_guide.py`，本目录用于满足内部 workflow 的测试边界声明，避免把普通对话入口误判为缺少验证。

最小验证命令：

```powershell
python -m unittest discover skills\lgwf-wf-tools\tests -p "test_lgwf_guide.py"
```
