# materialization_rules

- 复制源 skill 时排除 `.git`、`.lgwf`、`.local`、`reports`、`ws`、`__pycache__` 与 Python 缓存文件。
- 打包后必须内置 `vendor/lgwf-client-assist/`。
- 必须生成 `scripts/run_local_lgwf_workflow.py` 与 `PACKAGING_MANIFEST.json`。
- `ws/` 只作为运行目录占位，不能预写 `.lgwf/` 状态。

