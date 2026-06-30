# 目标 Workflow 直启

本文用于 `/lgwf-wf-tools run <path>`、`/lgwf-wf-tools target-run <path>` 和 `/lgwf-wf-tools --target-workflow <path>` 场景。

## 适用条件

只有用户明确使用以下形式时进入目标 workflow 直启：

- `/lgwf-wf-tools run <path>`
- `/lgwf-wf-tools target-run <path>`
- `/lgwf-wf-tools --target-workflow <path>`

自然语言中的“修复”“优化”“生成测试”“规划”“检查 prompt”等请求，即使包含 workflow 目录或 `workflow.lgwf` 路径，也先回到 [workflow-routing.md](workflow-routing.md)。

## 路径解析

- `<path>` 是 `workflow.lgwf` 文件时，直接作为目标 workflow。
- `<path>/workflow.lgwf` 存在时，使用该文件。
- `<path>/wf/workflow.lgwf` 存在时，使用该文件。
- `<package>/wf/workflow.lgwf` 对应 `<package>/ws`。
- `<dir>/workflow.lgwf` 对应 `<dir>/ws`。

如果无法解析出唯一目标 `workflow.lgwf`，报告解析失败原因，不回退到内部 workflow 路由。

## 已有运行目录

目标 `work_dir/.lgwf` 已存在时，先让用户选择：

- `continue`：继续当前 run。
- `resume`：恢复可恢复的历史 run。
- `rerun`：重新启动目标 workflow。

不要直接启动第二个 run。

## 启动与后续监控

直启路由使用本目录内置的 `vendor/lgwf-client-assist/scripts/lgwf.py`。第一版默认使用空输入 `{}`；需要复杂输入时，优先要求用户提供 UTF-8 JSON 文件。

启动后按 [facade-dispatch.md](facade-dispatch.md) 监控同一个 run handle。
