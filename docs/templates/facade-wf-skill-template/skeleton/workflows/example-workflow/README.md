# example-workflow

这是一个最小 LGWF workflow 示例，用于说明 facade registry 如何声明 runtime workflow。

## 输入

```json
{
  "request": {
    "message": "hello"
  }
}
```

## 入口

```powershell
python scripts\run_skill_workflow.py --workflow-id example-workflow --input-json-file input.json --lgwf-py <path-to-lgwf.py>
```

## 状态

运行状态写入 `ws/.lgwf/`。

## 替换方式

复制模板后，用真实 workflow 替换本目录，或删除本示例并更新 `registry.json`。
