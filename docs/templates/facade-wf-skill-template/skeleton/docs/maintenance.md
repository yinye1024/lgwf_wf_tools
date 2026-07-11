# 维护命令

本文件说明 facade 的维护入口。真实仓库复制模板后，应替换命令前缀和验证命令。

## 命令

| 命令 | 动作 |
| --- | --- |
| `/facade-template help` | 展示本文件摘要。 |
| `/facade-template list` | 运行 `python scripts\list_workflows.py`。 |
| `/facade-template doctor` | 运行 `python scripts\validate_registry.py`。 |

## 最小验证

```powershell
python scripts\validate_registry.py
python scripts\list_workflows.py
python tests\test_registry_template.py -v
```

## 发布前检查

- registry 中不存在无效路径。
- 内部 workflow 下没有额外 `SKILL.md`。
- `entry_contract.json` 与 registry 路径一致。
- 运行状态目录没有进入发布包基线。
