from typing import Any, TypedDict


WorkflowDsl = dict[str, Any]


class WorkflowPackagePayload(TypedDict):
    version: int
    source: str
    package_root: str
    entry_workflow: str
    workflow: WorkflowDsl
    workflows: dict[str, WorkflowDsl]

