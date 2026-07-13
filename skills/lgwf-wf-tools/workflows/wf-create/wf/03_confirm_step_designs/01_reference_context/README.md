# reference_context

## 职责

准备步骤设计和实现阶段需要的只读参考上下文，包括 facade 内置 DSL 规范、workflow 模块化创建指引和模块自包含契约。脚手架结构信息不在本阶段复制，后续节点直接消费 `.lgwf/scaffold_package_result.json`。

## 输入

- facade 内置 `vendor/lgwf-client-assist/references/dsl-assist/*`
- `docs/LGWF_WF_MODULAR_DEVELOPMENT.md`
- `workflows/01-share/module-contract.md`

## 输出

- `.lgwf/create_reference_context/dsl-assist/*.md`
- `.lgwf/create_reference_context/workflow-modular-development/LGWF_WF_MODULAR_DEVELOPMENT.md`
- `.lgwf/create_reference_context/module-contract/module-contract.md`
- `.lgwf/create_reference_context/step-design-reference-index.md`
- `.lgwf/create_reference_context/implementation-reference-index.md`

## 产物

所有产物写入当前 run 的 workspace，不写入 workflow source root，也不写入目标 package。

## 验证

```powershell
python -m unittest discover skills\lgwf-wf-tools\workflows\wf-create\tests
```

## 禁止事项

- 不生成步骤设计 proposal。
- 不读取或修改目标 package。
- 不读取或复用旧 run 的步骤设计草案；当前步骤设计只由 `.lgwf/step_designs_proposal.json` 承载。
