# 适配说明

复制 skeleton 后需要按目标仓库调整以下内容。

## 必改项

- `SKILL.md` frontmatter 的 `name` 和 `description`。
- `AGENTS.md` 中的 facade 名称、命令前缀和路由表。
- `README.md` 中的定位、入口和验证命令。
- `registry.json` 中的 workflow id、description、路径和 kind。
- 每个 `entry_contract.json` 中的 id、输入 schema、状态边界和产物。
- `scripts/run_skill_workflow.py` 中 runtime 获取方式。如果目标仓库内置 vendor，可改成固定路径；如果使用外部 runner，可保留 `--lgwf-py` 或 `LGWF_PY`。

## 可选项

- 如果目标仓库没有 LGWF runtime，只保留 `tool-workflow`，删除示例 `lgwf` workflow。
- 如果目标仓库已有测试体系，把 `tests/test_registry_template.py` 合并到现有测试目录。
- 如果目标仓库已有命令补全、doctor 或 package 脚本，可以把它们纳入 `docs/maintenance.md`。

## 不要照搬的内容

- 不要复制 `lgwf-wf-tools` 的业务 workflow id。
- 不要复制 `vendor/`。
- 不要把示例 `example-workflow` 保留在正式 registry 中。
- 不要把本机绝对路径写进 registry、entry contract 或 workflow resource path。

## 与现有多 skill 仓库的关系

多 skill 仓库可以先保留原 skill：

```text
skills/<facade>       统一入口和 registry
skills/<old-skill>    薄包装，说明何时直接使用或路由到 facade
modules/<business>    业务实现层
```

当 facade 路由稳定后，再决定是否减少旧 skill 暴露面。
