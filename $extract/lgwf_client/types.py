from typing import Any, Literal, NotRequired, TypedDict


InstructionType = Literal["shell", "python", "codex", "tool"]


class Instruction(TypedDict):
    id: str
    type: InstructionType
    cwd: NotRequired[str]
    ref_root: NotRequired[dict[str, Any]]
    payload: dict[str, Any]
    timeout_seconds: NotRequired[int | None]


class ExecutionResult(TypedDict):
    instruction_id: str
    ok: bool
    exit_code: int
    stdout: str
    stderr: str
    artifacts: list[dict[str, Any]]
    changed_files: list[str]
    metadata: dict[str, Any]


class WorkspaceFile(TypedDict):
    path: str
    size_bytes: int
    sha256: str


class WorkspaceContext(TypedDict):
    version: int
    workspace_root: str
    generated_at: str
    files: list[WorkspaceFile]
    stats: dict[str, Any]

