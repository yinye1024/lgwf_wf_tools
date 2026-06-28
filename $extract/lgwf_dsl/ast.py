from dataclasses import dataclass, field

import lgwf_dsl.diagnostics as diagnostics_module


@dataclass(frozen=True)
class StateRef:
    path: str
    location: diagnostics_module.SourceLocation | None = None


@dataclass(frozen=True)
class ResourceRef:
    type: str
    path: str
    root: str = "workspace"
    location: diagnostics_module.SourceLocation | None = None


@dataclass(frozen=True)
class ContextRef:
    resource: ResourceRef | None = None
    context_set: str | None = None
    location: diagnostics_module.SourceLocation | None = None


@dataclass(frozen=True)
class DefaultsDecl:
    ref_root: dict[str, str] = field(default_factory=lambda: {"root": "workflow", "path": "."})
    timeout_seconds: int = 300
    instruction_path_template: str = "instructions.{node}"
    result_path_template: str = "results.{node}"
    location: diagnostics_module.SourceLocation | None = None


@dataclass(frozen=True)
class ContextSetDecl:
    name: str
    resources: list[ResourceRef]
    location: diagnostics_module.SourceLocation | None = None


@dataclass(frozen=True)
class SandboxRootDecl:
    include: list[str]
    exclude: list[str] = field(default_factory=list)
    promote_include: list[str] = field(default_factory=list)
    location: diagnostics_module.SourceLocation | None = None


@dataclass(frozen=True)
class SandboxTargetDirDecl:
    root: str
    path: str
    include: list[str]
    exclude: list[str] = field(default_factory=list)
    promote_include: list[str] = field(default_factory=list)
    location: diagnostics_module.SourceLocation | None = None


@dataclass(frozen=True)
class SandboxDecl:
    path: str
    work_dir: SandboxRootDecl
    target_dir: SandboxTargetDirDecl | None = None
    result_path: StateRef | None = None
    location: diagnostics_module.SourceLocation | None = None


@dataclass(frozen=True)
class PythonDecl:
    id: str
    script_path: str
    timeout_seconds: int | None = None
    timeout_unlimited: bool = False
    instruction_path: StateRef | None = None
    result_path: StateRef | None = None
    updates_state: bool = False
    location: diagnostics_module.SourceLocation | None = None


@dataclass(frozen=True)
class ToolDecl:
    id: str
    tool_name: str
    options: dict[str, object] = field(default_factory=dict)
    timeout_seconds: int | None = None
    timeout_unlimited: bool = False
    result_path: StateRef | None = None
    location: diagnostics_module.SourceLocation | None = None


@dataclass(frozen=True)
class CodexDecl:
    id: str
    prompt_path: str
    contexts: list[ContextRef] = field(default_factory=list)
    target_dirs: list[str] = field(default_factory=list)
    target_files: list[str] = field(default_factory=list)
    target_dirs_path: StateRef | None = None
    target_files_path: StateRef | None = None
    output_json_path: str | None = None
    output_json_mode: str | None = None
    output_file_paths: list[str] = field(default_factory=list)
    timeout_seconds: int | None = None
    timeout_unlimited: bool = False
    instruction_path: StateRef | None = None
    result_path: StateRef | None = None
    location: diagnostics_module.SourceLocation | None = None


@dataclass(frozen=True)
class ApprovalDecl:
    id: str
    prompt: str | None
    prompt_ref_path: str | None
    read_path: StateRef
    write_path: StateRef
    result_path: StateRef | None = None
    persist_path: str | None = None
    route_on_decision: bool = False
    timeout_seconds: int | None = None
    timeout_unlimited: bool = False
    poll_interval_seconds: int | None = None
    location: diagnostics_module.SourceLocation | None = None


@dataclass(frozen=True)
class WorkflowRefDecl:
    id: str
    workflow_path: str
    result_path: StateRef | None = None
    location: diagnostics_module.SourceLocation | None = None


@dataclass(frozen=True)
class ReactSlotDecl:
    slot_name: str
    task: PythonDecl | ToolDecl | CodexDecl | WorkflowRefDecl
    location: diagnostics_module.SourceLocation | None = None


@dataclass(frozen=True)
class AgentLoopSlotDecl:
    slot_name: str
    task: PythonDecl | ToolDecl | CodexDecl | WorkflowRefDecl
    location: diagnostics_module.SourceLocation | None = None


@dataclass(frozen=True)
class ReactOnMaxAskDecl:
    prompt: str
    read_path: StateRef
    write_path: StateRef
    extra_max_steps: int
    result_path: StateRef | None = None
    status_path: StateRef | None = None
    timeout_seconds: int | None = None
    timeout_unlimited: bool = False
    poll_interval_seconds: int | None = None
    location: diagnostics_module.SourceLocation | None = None


@dataclass(frozen=True)
class ReactDecl:
    id: str
    max_steps: int
    slots: dict[str, ReactSlotDecl]
    spec_path: str | None = None
    on_max_ask: ReactOnMaxAskDecl | None = None
    location: diagnostics_module.SourceLocation | None = None


@dataclass(frozen=True)
class AgentLoopDecl:
    id: str
    max_iterations: int
    artifacts_path: str
    goal: str
    slots: dict[str, AgentLoopSlotDecl]
    slot_order: list[str]
    on_max: str = "block"
    on_error: str = "block"
    token_max: int = 1000000
    contexts: list[ContextRef] = field(default_factory=list)
    status_path: StateRef | None = None
    report_path: StateRef | None = None
    location: diagnostics_module.SourceLocation | None = None


@dataclass(frozen=True)
class ParallelStepDecl:
    id: str
    output_path: StateRef
    result_path: StateRef
    task: PythonDecl | ToolDecl | CodexDecl | ReactDecl | WorkflowRefDecl
    location: diagnostics_module.SourceLocation | None = None


@dataclass(frozen=True)
class ParallelDecl:
    id: str
    steps: list[ParallelStepDecl]
    max_concurrency: int | None = None
    fail_strategy: str | None = None
    location: diagnostics_module.SourceLocation | None = None


@dataclass(frozen=True)
class EdgeDecl:
    from_node: str
    to_node: str
    location: diagnostics_module.SourceLocation


@dataclass(frozen=True)
class FlowDecl:
    nodes: list[str]
    location: diagnostics_module.SourceLocation


@dataclass(frozen=True)
class RouteDecl:
    from_node: str
    branches: dict[str, str]
    location: diagnostics_module.SourceLocation


StatementDecl = (
    DefaultsDecl
    | ContextSetDecl
    | PythonDecl
    | ToolDecl
    | CodexDecl
    | ApprovalDecl
    | ReactDecl
    | AgentLoopDecl
    | WorkflowRefDecl
    | ParallelDecl
    | EdgeDecl
    | FlowDecl
    | RouteDecl
)


@dataclass(frozen=True)
class WorkflowAst:
    name: str | None
    entry_point: str
    statements: list[StatementDecl]
    sandbox: SandboxDecl | None = None
    location: diagnostics_module.SourceLocation | None = None
    source_name: str | None = None
