请审阅最终摘要草稿，并提交交付决策。

## 面向用户的展示要求

主 agent 到达本节点后，必须先用中文向用户展示“摘要预览 + 编号选择模板”，等待用户明确选择后再提交 approval。不要只展示 JSON；JSON 只作为内部提交值或高级用户参考。

如果 `delivery_review_input.selection_prompt` 存在，必须先原样展示该字段内容，再等待用户选择。不得改写、压缩或省略其中的 1-5 编号选项。

展示给用户的内容必须包含：

1. 本次摘要的目标仓库或作用域。
2. 变更文件数量。
3. 变更概览，至少 3 条；如果摘要不足 3 条，展示全部。
4. 关键文件，至少 5 个；如果摘要不足 5 个，展示全部。
5. 风险点，至少 2 条；如果摘要不足 2 条，展示全部。
6. 建议验证命令。
7. 建议 commit message 的英文版本和中文版本，以及简短理由。
8. 最后的编号选择模板。

如果 `delivery_review_input.final_change_brief_markdown` 或 `final_change_brief_markdown` 中已有这些 section，必须先从该 Markdown 提取并展示给用户；不要省略成“摘要已生成”。如果缺少某个 section，要明确写“未生成该部分”。

展示给用户时必须使用下面格式：

```text
本次变更摘要预览：

目标仓库：<repo_path 或 scoped_repo_path>
变更文件数：<changed_files_count>

变更概览：
- <overview 1>
- <overview 2>
- <overview 3>

关键文件：
- <file 1>：<说明>
- <file 2>：<说明>
- <file 3>：<说明>
- <file 4>：<说明>
- <file 5>：<说明>

风险点：
- <risk 1>
- <risk 2>

建议验证命令：
- <command 1>
- <command 2>
- <command 3>

建议 commit message（英文，默认用于 git commit -m）：
<commit_message_suggestion>

建议 commit message（中文，用于理解）：
<commit_message_suggestion_zh>

理由：
<commit_message_rationale>

请选择本次最终交付动作：

1. 只接受摘要
   结束 workflow，不执行 git add 或 git commit。

2. 加入暂存区
   接受摘要，并对当前确认范围执行 git add，不创建 commit。

3. 直接提交
   接受摘要，执行 git add，并用建议 commit message 创建 commit：
   <commit_message_suggestion>

4. 修订摘要
   不继续交付，请说明需要修改哪些摘要内容。

5. 拒绝交付
   结束本次 run，不接受当前摘要。

请回复 1、2、3、4 或 5。
```

用户回复编号后，主 agent 再转换成对应 JSON 提交：

- `1` -> `approval=approve`、`commit_action=none`
- `2` -> `approval=approve`、`commit_action=stage`
- `3` -> `approval=approve`、`commit_action=commit`，`commit_message` 使用用户确认的提交信息；若用户没有另行修改，使用 `commit_message_suggestion`
- `4` -> `approval=revise`，`changes` 使用用户说明
- `5` -> `approval=reject`

编号 `1`、`2`、`3`、`4`、`5` 只在本 REVIEW 节点等待用户输入时有效。workflow 已经结束后，用户再单独回复编号时，不得把编号解释成 Git 写操作；应提示用户重新运行 workflow 或明确给出新的命令和作用域。

## 选项语义

| 选项 | 含义 | 适用场景 |
| --- | --- | --- |
| `none` | 接受摘要并结束 workflow，不执行 `git add` 或 `git commit`。 | 只需要摘要结果，暂时不改 Git 暂存区和提交历史。 |
| `stage` | 接受摘要，并对当前确认的目标范围执行 `git add`。 | 已确认要把本次范围内变更放入暂存区，但暂时不创建 commit。 |
| `commit` | 接受摘要，先执行 `git add`，再用确认的 `commit_message` 执行 `git commit`。 | 已确认摘要和提交信息，并希望 workflow 直接创建提交。 |

要求：

- 仅接受 JSON object，作为 approval 的 `value` 提交。
- `approval` 只能是 `approve`、`revise` 或 `reject`。
- `commit_action` 只能是 `none`、`stage` 或 `commit`，缺省按 `none` 处理。
- `stage_scope` 只能写 `target_scope`，表示使用当前 Git 采集结果中的相对作用域；不得写任意路径。
- 当 `commit_action=commit` 时，`commit_message` 必须是非空字符串。
- 当当前确认范围是仓库根目录时，只有用户在本 REVIEW 节点明确确认根目录写操作，才允许提交 JSON 带 `allow_repo_root_write=true`；否则保持缺省或 `false`。
- `comment` 用中文说明原因。
- 若选择 `revise`，请在 `changes` 数组中列出需要补充的点。

`approve` 表示接受当前 Markdown 草稿并进入最终整理；`revise` 表示继续在本阶段内修订；`reject` 表示当前 run 不应继续交付。

## 可选提交模板

### 选项 A：只接受摘要，不执行 Git 写操作

```json
{
  "approval": "approve",
  "commit_action": "none",
  "stage_scope": "target_scope",
  "commit_message": "",
  "changes": [],
  "comment": "接受摘要，不执行 git add 或 git commit。"
}
```

### 选项 B：接受摘要，并执行 git add

```json
{
  "approval": "approve",
  "commit_action": "stage",
  "stage_scope": "target_scope",
  "commit_message": "",
  "changes": [],
  "comment": "接受摘要，并将当前确认范围内的变更加入暂存区。"
}
```

### 选项 C：接受摘要，并执行 git commit

```json
{
  "approval": "approve",
  "commit_action": "commit",
  "stage_scope": "target_scope",
  "commit_message": "<使用建议 commit message 或人工确认后的提交信息>",
  "changes": [],
  "comment": "接受摘要，并使用确认的 commit message 创建提交。"
}
```

### 需要修订摘要

```json
{
  "approval": "revise",
  "commit_action": "none",
  "stage_scope": "target_scope",
  "commit_message": "",
  "changes": ["列出需要补充或修改的摘要内容"],
  "comment": "当前摘要还需要修订，暂不执行 git add 或 git commit。"
}
```

### 拒绝交付

```json
{
  "approval": "reject",
  "commit_action": "none",
  "stage_scope": "target_scope",
  "commit_message": "",
  "changes": [],
  "comment": "拒绝当前摘要交付，结束本次 run。"
}
```
