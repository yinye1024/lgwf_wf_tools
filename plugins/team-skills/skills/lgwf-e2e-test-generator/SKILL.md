---
name: lgwf-e2e-test-generator
description: 为任意目标 LGWF workflow 生成固定三类端到端测试：脚本级全分支、runtime fake Codex、真实 Codex 正向闭环。
---

# lgwf-e2e-test-generator

本 skill 通过 `workflow.lgwf` 运行。它会读取目标 workflow package，生成覆盖矩阵，并固定产出三类端到端测试脚本。

## 使用场景

- 想为一个已有 LGWF workflow 快速生成端到端测试骨架。
- 想把脚本级分支覆盖、runtime 编排覆盖和真实 Codex 正向验收拆开。
- 想规范 fake Codex 的输入输出契约，避免依赖调用顺序或 Windows 命令行长参数。

## 运行方式

通过 `lgwf-client-assist` 的 `lgwf.py run --workflow-lgwf` 启动本 workflow，并在入口 approval 中提交目标 workflow 信息。

## 输出约束

- 固定生成三类测试，不提供裁剪开关。
- `runtime_fake_e2e` 必须使用 Python fake Codex，prompt 通过 `--prompt-file` 传递。
- `real_positive_e2e` 默认跳过，只有环境变量显式打开时才运行真实 Codex。
