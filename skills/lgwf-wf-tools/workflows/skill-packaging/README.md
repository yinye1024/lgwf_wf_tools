# Skill Packaging Workflow

`skill-packaging` 是 registry 管理的 `tool_workflow`，目标是把已有 LGWF workflow Codex skill 打包成自包含 skill。它不是 LGWF runtime workflow，不通过 `lgwf.py run` 启动；当前执行入口是 `scripts/package_lgwf_skill.py`。

## 模块定位

- 模块类型：`tool_workflow`
- 目标：读取源 skill、复制 bundled runtime、生成打包清单、校验输出目录
- 当前状态：以脚本入口为准；`wf/` 目录保留为历史设计材料，不作为 registry 运行入口

## 目录结构

```text
skill-packaging/
  AGENTS.md
  README.md
  entry_contract.json
  scripts/
  tests/
  wf/
    ...
```

## 入口与边界

- registry 入口：`registry.json` 中的 `skill-packaging`。
- 脚本入口：`scripts/package_lgwf_skill.py`。
- 必填参数：`--source-skill` 和 `--output-parent`。
- 可选参数：`--runtime-source` 和 `--force`。
- 运行期不维护 LGWF `work_dir`，只允许写入 `output_parent/source_skill_name`。
- 未显式传入 `--force` 时，不得覆盖已有输出目录。

## 最小验证

```powershell
python -m unittest discover skills\lgwf-wf-tools\workflows\skill-packaging\tests -p test_scaffold_package_rules.py
python skills\lgwf-wf-tools\workflows\skill-packaging\scripts\package_lgwf_skill.py --help
```

## 剩余工作

- 补充真实打包样例和 audit smoke。
- 在后续迭代中清理或归档 `wf/` 历史设计材料。
- 继续完善输出清单的契约测试。
