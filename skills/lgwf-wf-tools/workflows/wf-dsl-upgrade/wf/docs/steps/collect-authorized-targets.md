# collect-authorized-targets

## step_slug
`collect-authorized-targets`

## step_name
授权目标收集与范围校验

## goal
设计 `wf/01_collect_targets/workflow.lgwf`，把入口 `dsl_upgrade_target` 解析、目标路径归一化、`allowed_dirs` 越权保护、`scope_mode` 分流和 `max_targets` 限制固化成唯一授权闸门，生成后续全部阶段都必须复用的 `target_manifest.json` 与 `target_scope_validation.json`。

## inputs
- 上游阶段或节点：
  - `.lgwf/business_flow.json` 中 `collect_authorized_targets` 阶段定义
- 依赖文件或状态：
  - `docs_tmp/wf-dsl-upgrade-development.md`
  - `.lgwf/create_reference_context/dsl-assist/create-workflow.md`
  - `.lgwf/create_reference_context/scaffold/scaffold_template_spec.md`
  - `.lgwf/create_reference_context/workflow-modular-development/LGWF_WF_MODULAR_DEVELOPMENT.md`
- 关键约束：
  - 只允许处理已授权目录中的 `workflow.lgwf`
  - `mode=apply` 缺少 `allowed_dirs` 时必须失败或输出明确 validation failed
  - 运行状态只允许写入 `ws/.lgwf`
  - 第一版保留 `scope_mode=registry` 契约，但不得默默伪装成 `explicit`

## outputs
- 预期生成的文件：
  - `wf/01_collect_targets/workflow.lgwf`
  - `wf/01_collect_targets/scripts/*.py`
  - `wf/01_collect_targets/resources/*`
  - `ws/.lgwf/target_manifest.json`
  - `ws/.lgwf/target_scope_validation.json`
- 预期生成的目录：
  - `wf/01_collect_targets/agents/`
  - `wf/01_collect_targets/scripts/`
  - `wf/01_collect_targets/resources/`
- 交付给下游的结构片段：
  - manifest 中的原始路径、resolved path、mode、scope_mode、allowed_dirs、target_count、per-target hash 和 `authorized` 标记
  - validation 中的 `passed`、`reasons`、`target_count` 和越权摘要

## dependencies
- 前置步骤：
  - `define-shared-helper-and-verification`
- 依赖节点：
  - 入口 `dsl_upgrade_target`
  - 根 workflow 对阶段目录和状态边界的约束
- 需要人工确认的位置：
  - 当前阶段不引入人工确认；如遇无法安全支持的 registry 解析策略，只能通过结构化 validation 或后续 summary 暴露

## implementation_suggestions
- 优先使用阶段脚本加共享 helper 处理路径规范化、存在性检查、`allowed_dirs` 校验和 hash 计算，把业务判断留在阶段内部而不是根 workflow。
- `scope_mode=explicit` 作为第一版主路径，`scope_mode=registry` 至少要保留字段校验和显式分支；若当前轮无法安全实现 registry 扫描，应返回可审计的 unsupported/validation 结果。
- manifest 只引用目标 package 之外的被授权 workflow 文件，禁止写入任何源码树级 `.lgwf` 或缓存目录。
- 阶段资源中补充清单字段说明和错误文案模板，确保后续 `02_confirm_scope`、`03_upgrade_one_target`、summary 和测试复用同一结构。

## acceptance_notes
- 重点确认 manifest 是后续全部阶段唯一目标来源，后续阶段不得重新扫目录或自行扩展目标集合。
- 重点确认 `allowed_dirs` 校验在 `dry_run` 和 `apply` 都成立，只是 `apply` 对缺失 `allowed_dirs` 更严格。
- 若第一版 registry 模式只保留契约不提供真实展开能力，必须在本步骤文档和 summary 路径中显式记录，不得静默降级。

## out_of_scope
- `lgwf-wf-prompt-fix`
- `lgwf-wf-tools`
- 自动修复、自动重试或端到端运行保证
- 直接执行 audit、写入升级规则或修改目标文件
