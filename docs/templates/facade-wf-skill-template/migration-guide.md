# 迁移指南

本文说明如何把现有 skill 仓库迁移到 facade workflow skill 模式。

## 迁移顺序

1. 盘点现状：列出对外 skill、业务模块、脚本、workflow、测试和输出目录。
2. 定义 facade：确定唯一入口 skill，并保持 `SKILL.md` 精简。
3. 建立 registry：为每个稳定业务能力分配 workflow id。
4. 补 entry contract：为每个 workflow id 写清输入、状态、产物和恢复规则。
5. 抽共享规则：把审批、产物、registry、dispatch、monitor 规则放入 `workflows/01-share/`。
6. 接入 runner：用 `scripts/run_skill_workflow.py` 或目标仓库已有 runner 统一启动。
7. 加验证：用 `scripts/validate_registry.py` 固化 registry 和 contract 门禁。
8. 分批替换旧入口：保留旧 skill 为薄包装，逐步引导到 facade。

## 目录映射

推荐新结构：

```text
<facade-skill>/
  SKILL.md
  AGENTS.md
  README.md
  registry.json
  docs/
  scripts/
  tests/
  workflows/
    01-share/
    <workflow-id>/
      AGENTS.md
      README.md
      entry_contract.json
      wf/
      ws/
```

如果目标仓库已有 `modules/<business>/`，可以保留实现层，把 registry workflow 指向现有模块的 workflow 或脚本，不必立即搬目录。

## workflow id 选择

优先为稳定用户意图建 id，例如：

- `index`
- `ingest`
- `lint`
- `query`
- `relationship-review`
- `self-improve`

不要为每个内部脚本建 id。registry 管的是用户可派发能力，不是技术文件清单。

## `lgwf` 与 `tool-workflow`

使用 `lgwf`：

- 有 `workflow.lgwf`。
- 需要运行状态、resume、approval 或多节点编排。
- 有固定 `work_dir`。

使用 `tool-workflow`：

- 由脚本或文档入口驱动。
- 不走 LGWF runtime。
- 只需要 registry 纳管和入口契约。

## 最小验收

迁移一个 workflow id 后至少检查：

- registry 条目存在且路径相对。
- `entry_contract.json` 的 `id`、`kind`、路径和 registry 一致。
- `AGENTS.md` 说明定位、入口、依赖、状态边界、产物、验证和禁止事项。
- `work_dir` 不等于源码目录。
- 运行 `python scripts\validate_registry.py` 通过。

## 分阶段策略

第一阶段只新增 facade 和 registry，不删除旧 skill。

第二阶段把旧 skill 文档改成薄包装，指向 facade 或目标 workflow。

第三阶段补齐 self-improve、e2e 和发布前检查。

第四阶段再考虑是否清理旧目录或重复说明。
