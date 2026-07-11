# example-tool-workflow

这是一个最小脚本型 workflow 示例，用于说明 `kind=tool-workflow` 的 registry 条目。

## 输入

命令行参数：

- `--message`：要写入结果的消息。
- `--output`：结果 JSON 路径。

## 输出

```json
{
  "status": "ok",
  "message": "hello"
}
```

## 替换方式

复制模板后，用真实脚本入口替换本目录，或删除本示例并更新 `registry.json`。
