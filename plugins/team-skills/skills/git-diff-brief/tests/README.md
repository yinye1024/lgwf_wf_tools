# 测试说明

当前测试只覆盖初稿 package 的结构边界和少量脚本纯函数：

- 根目录不暴露 `SKILL.md` 或根 `workflow.lgwf`
- `wf/` 作为唯一 workflow root，且四个业务阶段都落在第一层
- 关键脚本的路径归一化、变更文件索引和最终结果整理逻辑

建议从仓库根目录运行：

```powershell
python -m unittest discover plugins\team-skills\skills\git-diff-brief\tests
```
