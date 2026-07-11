# skill-packaging self-improve

本目录保存 `skill-packaging` 的最小自包含自检入口。它只检查本 workflow package 的入口文档、入口契约、workflow root、work dir 和测试目录是否存在，不调用 facade 级 self-improve。

## 入口

```powershell
python self-improve\scripts\self_improve.py check
```

## 状态边界

运行报告写入本 workflow package 的 `.local/self-improve/`，不得写入 `ws/.lgwf/` 或打包产物目录。
