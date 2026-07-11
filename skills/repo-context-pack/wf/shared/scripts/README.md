# shared scripts

`repo_context_runtime.py` 放置四个阶段共用的稳定技术逻辑，包括请求归一化、调用 `scripts/build_context_pack.py`、输出校验和运行摘要写入。

共享目录不得放置阶段私有 prompt、人工确认文案或运行态文件。
