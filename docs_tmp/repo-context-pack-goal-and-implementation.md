# repo-context-pack 的 wf-create 输入说明

## 0. 给 wf-create 的解释规则

本文是 `wf-create` 的 `target_file` 参考资料，只用于创建 `repo-context-pack` 这个目标 package。

读取本文时必须遵守以下解释规则：

- 本文不是待执行计划，不要求当前 `wf-create` 节点运行本文中的命令。
- 本文不是外部通用规划、需求澄清或实现策划流程入口。
- 本文中的验证命令只是应写入目标 package 文档和测试说明的验收命令，除非 `wf-create` 已进入最终实现验证节点，否则不要执行。
- 本文中的目录结构、阶段、脚本和测试是目标 package 的生成规格，不是要求修改 `wf-create` 自身。
- 不要根据本文创建额外设计计划、额外实现计划或本文没有声明的流程文档。
- 不要修改 `skills/lgwf-wf-tools/`、`registry.json`、`vendor/` 或 facade 共享运行时。

目标输出目录固定为：

```text
D:/allen/github/lgwf_wf_tools/skills/repo-context-pack
```

该目录可以被完整重建。生成内容必须限制在上述目录内。

## 1. 创建目标

创建一个名为 `repo-context-pack` 的 Codex skill。该 skill 自带一个内嵌 LGWF workflow，用于只读扫描指定仓库或模块目录，并生成 AI agent 接手该目标时需要的上下文包。

模块类型：

- 外层模块：`codex_skill`
- 内嵌模块：`lgwf_workflow_package`

目标用户：

- 准备接手陌生仓库的 AI agent。
- 准备修改某个模块前需要快速建立上下文的 agent。
- 做代码 review、workflow review 或 handoff 的 agent。
- 编写或维护 LGWF workflow package 的 agent。

核心价值：

- 快速收集目标目录入口、模块地图、命令、风险和推荐阅读顺序。
- 用固定结构产物降低后续修改、review、handoff 或 workflow-authoring 的上下文成本。
- 保持只读扫描，不改变被分析的目标源码。

## 2. 明确非目标

第一版不要实现以下能力：

- 不修改 `target_dir` 内源码。
- 不修复目标仓库 bug。
- 不为目标仓库生成测试。
- 不执行 Git 写操作。
- 不注册 `lgwf-wf-tools/registry.json`。
- 不自动发布、部署或提交。
- 不对大型 monorepo 做完整语义理解。
- 不复制 `.git`、`.lgwf`、`vendor`、`.venv`、`node_modules`、`ws` 等目录进入上下文包。
- 不依赖 Codex prompt 直接扫描目标仓库；扫描和渲染应由确定性 Python 脚本完成。

## 3. 目标目录结构

`wf-create` 应在 `skills/repo-context-pack/` 下生成以下结构：

```text
skills/repo-context-pack/
  SKILL.md
  AGENTS.md
  README.md
  entry_contract.json
  scripts/
    build_context_pack.py
  tests/
    test_build_context_pack.py
  ws/
  wf/
    workflow.lgwf
    artifact_contracts.json
    shared/
      scripts/
        repo_context_runtime.py
    01_entry_scope_resolution/
      workflow.lgwf
      scripts/
        run.py
    02_target_context_inventory/
      workflow.lgwf
      scripts/
        run.py
    03_context_pack_rendering/
      workflow.lgwf
      scripts/
        run.py
    04_workflow_summary_handoff/
      workflow.lgwf
      scripts/
        run.py
```

结构要求：

- 外层 package 根目录不得放置可运行的 `workflow.lgwf`。
- 唯一根 workflow 是 `wf/workflow.lgwf`。
- 阶段 workflow 只出现在 `wf/<stage>/workflow.lgwf`。
- 不要创建孙级 `workflow.lgwf`。
- 运行状态只写入 `skills/repo-context-pack/ws/.lgwf/`。
- 源码、测试、脚本和 workflow 定义必须与 `ws/.lgwf/` 分离。

## 4. Skill 入口契约

`SKILL.md` 应把该模块声明为一个用于生成仓库上下文包的 Codex skill。

触发意图：

- 用户要求生成 repo context pack。
- 用户要求分析仓库结构、模块入口、命令、风险和阅读顺序。
- 用户准备接手、review、修改或 handoff 一个仓库或 workflow package。

`AGENTS.md` 和 `README.md` 必须说明：

- 模块定位。
- 入口方式。
- 输入字段。
- 运行状态目录。
- 输出产物。
- 最小验证命令。
- 禁止修改目标源码、禁止注册 facade registry、禁止写错状态目录。

## 5. 输入契约

`entry_contract.json` 应声明 JSON object 输入。

必填字段：

- `target_dir`：要分析的仓库或模块目录。

可选字段：

- `output_dir`：上下文包输出目录。未提供时默认使用 `target_dir/.local/context-packs/<target_dir_name>`。
- `focus`：上下文包用途，允许值为 `onboarding`、`modification`、`review`、`workflow-authoring`、`handoff`，默认 `onboarding`。
- `depth`：扫描深度，允许值为 `light`、`normal`、`deep`，默认 `normal`。
- `max_files`：最大扫描文件数，默认 `1600`。
- `notes`：用户补充说明，默认空字符串。

输入示例：

```json
{
  "target_dir": "D:/allen/github/lgwf_wf_tools",
  "output_dir": "D:/allen/github/lgwf_wf_tools/.local/context-packs/lgwf_wf_tools",
  "focus": "workflow-authoring",
  "depth": "normal",
  "max_files": 1600,
  "notes": ""
}
```

非法输入处理：

- `target_dir` 不存在或不是目录时失败。
- `focus` 不在允许值内时失败。
- `depth` 不在允许值内时失败。
- `max_files` 不是正整数时失败。

## 6. 输出产物契约

上下文包输出目录固定包含七个文件：

- `repo_context_pack.md`：主上下文报告。
- `agent_handoff.md`：给下一个 agent 的交接摘要。
- `module_map.json`：入口文件和模块目录地图。
- `command_inventory.json`：从文档、脚本和配置中抽取的命令清单。
- `risk_register.md`：风险标记、人工确认、TODO/FIXME 等候选。
- `read_order.md`：推荐阅读顺序。
- `summary.json`：扫描统计和产物索引。

LGWF 运行态产物固定写入 `skills/repo-context-pack/ws/.lgwf/`：

- `.lgwf/repo_context_pack_request.json`
- `.lgwf/context_inventory.json`
- `.lgwf/context_pack_generation.json`
- `.lgwf/repo_context_pack_summary.json`

LGWF 报告产物：

- `ws/reports/repo-context-pack/report.md`

## 7. Workflow 业务流

根 `wf/workflow.lgwf` 只负责薄编排，按顺序调用四个阶段。

| 阶段目录 | 阶段目标 | 主要输入 | 主要输出 |
| --- | --- | --- | --- |
| `01_entry_scope_resolution` | 读取并校验输入，归一化默认值和路径。 | stdin 或 input JSON | `.lgwf/repo_context_pack_request.json` |
| `02_target_context_inventory` | 只读遍历目标目录，抽取入口、模块、命令、风险和阅读顺序。 | `.lgwf/repo_context_pack_request.json` | `.lgwf/context_inventory.json` |
| `03_context_pack_rendering` | 调用确定性渲染逻辑生成上下文包七个固定产物。 | `.lgwf/context_inventory.json` | `.lgwf/context_pack_generation.json` 和输出目录文件 |
| `04_workflow_summary_handoff` | 校验产物完整性并生成运行摘要。 | `.lgwf/context_pack_generation.json` | `.lgwf/repo_context_pack_summary.json` 和 `ws/reports/repo-context-pack/report.md` |

业务流要求：

- 阶段之间通过 `.lgwf/` 中声明的 JSON 产物传递状态。
- 每个阶段的脚本放在本阶段 `scripts/run.py`。
- 跨阶段可复用的纯函数放在 `wf/shared/scripts/repo_context_runtime.py`。
- 不需要人工确认节点。
- 不需要 Codex prompt 节点参与目标仓库扫描。

## 8. 扫描规则

扫描逻辑由 Python 确定性实现。

目录深度：

- `light`：最多 2 层。
- `normal`：最多 4 层。
- `deep`：最多 8 层。

扫描上限：

- 使用 `max_files` 控制最多收集文件数。
- 达到上限后应在 `summary.json` 或报告中标记截断状态。

必须跳过的目录：

- `.git`
- `.lgwf`
- `.venv`
- `venv`
- `node_modules`
- `vendor`
- `__pycache__`
- `ws`

必须跳过的文件类型：

- Python bytecode。
- 可执行二进制。
- 图片。
- 压缩包。
- 常见大体积二进制文件。

入口识别候选：

- `README.md`
- `AGENTS.md`
- `SKILL.md`
- `pyproject.toml`
- `package.json`
- `workflow.lgwf`

模块识别候选：

- `tests`
- `scripts`
- `docs`
- `wf`
- `workflows`
- `skills`
- Python package 目录。

命令抽取候选：

- `python`
- `pytest`
- `unittest`
- `npm`
- `pnpm`
- `yarn`
- `uv`
- `ruff`
- `mypy`
- `lgwf.py`

风险标记候选：

- `TODO`
- `FIXME`
- `HACK`
- `deprecated`
- `manual`
- `approval`
- `risk`

## 9. 渲染规则

Markdown 产物要求：

- 使用中文标题和说明。
- 短章节优先，不复制大段源码。
- 明确目标目录、扫描参数、截断状态、关键入口、推荐阅读顺序和风险候选。

JSON 产物要求：

- 使用 UTF-8 no BOM。
- 保持可被 `json.loads` 解析。
- 路径字段优先使用相对 `target_dir` 的路径；必要时保留归一化绝对路径。
- `summary.json` 必须包含输入参数、扫描文件数、截断状态和产物列表。

`read_order.md` 生成顺序：

1. 入口文件。
2. 重要说明文件。
3. 核心模块目录。
4. 测试和脚本目录。
5. 风险或人工确认相关文件。

## 10. 写入边界

生成后的 `repo-context-pack` 必须保持以下写入边界：

- `target_dir` 只读。
- 上下文包文件只写入 `output_dir`。
- LGWF 运行状态只写入 `skills/repo-context-pack/ws/.lgwf/`。
- 不在 `target_dir` 根目录写 `.lgwf`、`.tmp`、`__pycache__` 或其他缓存。
- 如果默认 `output_dir` 位于 `target_dir/.local/context-packs/...`，这是用户指定的上下文包输出位置，不等同于修改目标源码。

## 11. 直接脚本入口

`scripts/build_context_pack.py` 必须支持直接运行：

```powershell
python skills\repo-context-pack\scripts\build_context_pack.py `
  --target-dir D:\path\to\repo `
  --output-dir D:\path\to\repo\.local\context-packs\repo `
  --focus workflow-authoring `
  --depth normal
```

直接脚本入口应复用与 LGWF workflow 相同的核心扫描和渲染逻辑。

## 12. LGWF 入口

生成后的 workflow 应支持以下运行方式：

```powershell
python skills\lgwf-wf-tools\vendor\lgwf-client-assist\scripts\lgwf.py run `
  --workflow-lgwf skills\repo-context-pack\wf\workflow.lgwf `
  --work-dir skills\repo-context-pack\ws `
  --input-json-file request.json
```

注意：该命令是目标 package 的使用说明，不是要求 `wf-create` 在读取本文时执行。

## 13. 最小测试

生成 `tests/test_build_context_pack.py`，至少覆盖：

- `target_dir` 不存在时报错。
- `focus` 非法时报错。
- `depth` 非法时报错。
- 运行后输出目录包含七个固定产物。
- JSON 产物可解析。
- `summary.json` 中 `target_dir`、`output_dir`、`focus`、`depth`、`max_files` 与请求一致。
- `ws/.lgwf/repo_context_pack_summary.json` 标记 `passed=true`。
- 当 `output_dir` 不在 `target_dir` 内时，目标源码目录不出现 `.lgwf`、`.tmp` 或运行缓存。

## 14. 验收命令

以下命令应写入生成后的 `README.md` 或 `AGENTS.md`，作为目标 package 的验收方式：

```powershell
python skills\lgwf-wf-tools\vendor\lgwf-client-assist\scripts\lgwf.py audit skills\repo-context-pack\wf\workflow.lgwf
python -m unittest discover skills\repo-context-pack\tests
python -m compileall -q skills\repo-context-pack
```

注意：这些命令不是 `wf-create` 需求确认、业务流确认或步骤设计节点的执行任务。

## 15. 第一版完成定义

当 `wf-create` 完成目标 package 初稿后，应满足：

- `skills/repo-context-pack/SKILL.md`、`AGENTS.md`、`README.md` 和 `entry_contract.json` 存在。
- `skills/repo-context-pack/scripts/build_context_pack.py` 存在并可直接运行。
- `skills/repo-context-pack/wf/workflow.lgwf` 存在并只做阶段编排。
- 四个阶段目录各自包含 `workflow.lgwf` 和 `scripts/run.py`。
- `skills/repo-context-pack/wf/artifact_contracts.json` 声明关键运行产物。
- `skills/repo-context-pack/tests/test_build_context_pack.py` 覆盖最小验收。
- 目标 package 不依赖修改 `lgwf-wf-tools` facade registry。
- 目标 package 不把业务逻辑塞进 `wf-create`。

## 16. 暂不纳入第一版

以下增强可以在后续独立任务中考虑，但不要纳入本次 `wf-create` 初稿：

- 对大型 monorepo 做复杂采样策略。
- 对 Python、Node、LGWF DSL 做深层语义分析。
- 给 `command_inventory.json` 增加完整 `source_line`、`kind`、`confidence`、`purpose` 模型。
- 给 `risk_register.md` 增加复杂风险分级。
- 增加多种 golden fixture。
- 将 `repo-context-pack` 注册进 `lgwf-wf-tools/registry.json`。
