# Candidate 循环说明

- 只修改 candidate 副本
- `REACT` 的 `OBSERVE` 负责重新执行 candidate audit
- `DECIDE` 同时受 `attempt_policy.max_attempts` 和 `MAX 20` 的硬保护约束
