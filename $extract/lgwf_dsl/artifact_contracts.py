from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass
from typing import Any, Iterable

import lgwf_dsl.ast as ast_module
import lgwf_dsl.diagnostics as diagnostics_module
import lgwf_dsl.parser as parser_module
import lgwf_dsl.validator as validator_module


CONTRACT_FILE = "artifact_contracts.json"


@dataclass(frozen=True)
class ArtifactRef:
    path: str
    node_id: str
    source: str
    location: diagnostics_module.SourceLocation | None = None


class ArtifactContractAuditor:
    """Checks workspace .lgwf file consumers have explicit producers."""

    def __init__(self, package_root: str | pathlib.Path) -> None:
        self.package_root = pathlib.Path(package_root).resolve()
        self._visited_workflows: set[pathlib.Path] = set()
        self._declared_script_write_nodes: set[str] = set()
        self._python_node_ids: set[str] = set()

    def audit(self, ast: ast_module.WorkflowAst) -> list[diagnostics_module.Diagnostic]:
        diagnostics: list[diagnostics_module.Diagnostic] = []
        producers: dict[str, list[ArtifactRef]] = {}
        consumers: list[ArtifactRef] = []
        self._declared_script_write_nodes = set()
        self._python_node_ids = set()
        context_sets = self._context_sets(ast)
        source_dir = self._source_dir_for_ast(ast)
        self._collect_contract_file(producers, diagnostics)
        self._collect_workflow(ast, source_dir, context_sets, producers, consumers, diagnostics)
        self._validate_script_write_nodes(diagnostics)

        for consumer in consumers:
            if not self._has_producer(producers, consumer):
                diagnostics.append(
                    diagnostics_module.Diagnostic(
                        f"{consumer.source} consumes workspace artifact without an explicit producer: {consumer.path}",
                        consumer.location,
                        severity="error",
                        code="LGWF_ARTIFACT_CONTRACT_MISSING",
                        suggestion=(
                            "Add an upstream OUTPUT_JSON, APPROVAL PERSIST, or artifact_contracts.json "
                            "bootstrap_inputs/script_writes declaration for this .lgwf file or directory."
                        ),
                    )
                )
        return diagnostics

    def _collect_contract_file(
        self,
        producers: dict[str, list[ArtifactRef]],
        diagnostics: list[diagnostics_module.Diagnostic],
    ) -> None:
        path = self.package_root / CONTRACT_FILE
        if not path.is_file():
            return
        try:
            raw = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception as exc:
            diagnostics.append(self._invalid_contract(f"{CONTRACT_FILE} is not valid JSON: {exc}"))
            return
        if not isinstance(raw, dict):
            diagnostics.append(self._invalid_contract(f"{CONTRACT_FILE} root must be an object."))
            return

        bootstrap_inputs = raw.get("bootstrap_inputs", [])
        if not self._is_string_list(bootstrap_inputs):
            diagnostics.append(self._invalid_contract("bootstrap_inputs must be a list of strings."))
        else:
            for item in bootstrap_inputs:
                self._add_producer(producers, item, "<bootstrap>", "artifact_contracts.bootstrap_inputs")

        script_writes = raw.get("script_writes", {})
        if not isinstance(script_writes, dict):
            diagnostics.append(self._invalid_contract("script_writes must be an object."))
            return
        for node_id, writes in script_writes.items():
            if not isinstance(node_id, str) or not self._is_string_list(writes):
                diagnostics.append(self._invalid_contract("script_writes values must be lists of strings."))
                continue
            self._declared_script_write_nodes.add(node_id)
            for item in writes:
                self._add_producer(producers, item, node_id, "artifact_contracts.script_writes")

    def _collect_workflow(
        self,
        ast: ast_module.WorkflowAst,
        source_dir: pathlib.Path,
        context_sets: dict[str, ast_module.ContextSetDecl],
        producers: dict[str, list[ArtifactRef]],
        consumers: list[ArtifactRef],
        diagnostics: list[diagnostics_module.Diagnostic],
    ) -> None:
        source_path = pathlib.Path(ast.source_name).resolve() if ast.source_name else None
        if source_path is not None:
            if source_path in self._visited_workflows:
                return
            self._visited_workflows.add(source_path)

        for statement in ast.statements:
            self._collect_statement(statement, source_dir, context_sets, producers, consumers, diagnostics)

    def _collect_statement(
        self,
        statement: ast_module.StatementDecl,
        source_dir: pathlib.Path,
        context_sets: dict[str, ast_module.ContextSetDecl],
        producers: dict[str, list[ArtifactRef]],
        consumers: list[ArtifactRef],
        diagnostics: list[diagnostics_module.Diagnostic],
    ) -> None:
        if isinstance(statement, ast_module.CodexDecl):
            self._collect_codex(statement, context_sets, producers, consumers)
        elif isinstance(statement, ast_module.PythonDecl):
            self._python_node_ids.add(statement.id)
        elif isinstance(statement, ast_module.ApprovalDecl):
            if statement.persist_path is not None:
                self._add_producer(producers, statement.persist_path, statement.id, "APPROVAL PERSIST", statement.location)
        elif isinstance(statement, ast_module.ReactDecl):
            for slot in statement.slots.values():
                self._collect_statement(slot.task, source_dir, context_sets, producers, consumers, diagnostics)
        elif isinstance(statement, ast_module.AgentLoopDecl):
            self._collect_contexts(statement.id, statement.contexts, context_sets, consumers)
            for slot in statement.slots.values():
                self._collect_statement(slot.task, source_dir, context_sets, producers, consumers, diagnostics)
        elif isinstance(statement, ast_module.ParallelDecl):
            for step in statement.steps:
                self._collect_statement(step.task, source_dir, context_sets, producers, consumers, diagnostics)
        elif isinstance(statement, ast_module.WorkflowRefDecl):
            self._collect_child_workflow(statement, source_dir, producers, consumers, diagnostics)

    def _collect_codex(
        self,
        task: ast_module.CodexDecl,
        context_sets: dict[str, ast_module.ContextSetDecl],
        producers: dict[str, list[ArtifactRef]],
        consumers: list[ArtifactRef],
    ) -> None:
        if task.output_json_path is not None:
            self._add_producer(producers, task.output_json_path, task.id, "CODEX OUTPUT_JSON", task.location)
        for output_path in task.output_file_paths:
            self._add_producer(producers, output_path, task.id, "CODEX OUTPUT_FILE", task.location)
        self._collect_contexts(task.id, task.contexts, context_sets, consumers)

    def _validate_script_write_nodes(self, diagnostics: list[diagnostics_module.Diagnostic]) -> None:
        for node_id in sorted(self._declared_script_write_nodes):
            if node_id in self._python_node_ids:
                continue
            diagnostics.append(
                self._invalid_contract(
                    f"script_writes declares unknown PY node: {node_id}."
                )
            )

    def _collect_contexts(
        self,
        node_id: str,
        contexts: Iterable[ast_module.ContextRef],
        context_sets: dict[str, ast_module.ContextSetDecl],
        consumers: list[ArtifactRef],
    ) -> None:
        for resource in self._expand_contexts(contexts, context_sets):
            path = self._artifact_path(resource.path)
            if resource.root == "workspace" and path is not None:
                if resource.type == "file":
                    consumers.append(ArtifactRef(path, node_id, "CONTEXT workspace file", resource.location))
                elif resource.type == "dir":
                    consumers.append(ArtifactRef(path, node_id, "CONTEXT workspace dir", resource.location))

    def _has_producer(self, producers: dict[str, list[ArtifactRef]], consumer: ArtifactRef) -> bool:
        if consumer.path in producers:
            return True
        if consumer.source != "CONTEXT workspace dir":
            return False
        prefix = consumer.path.rstrip("/") + "/"
        return any(path.startswith(prefix) for path in producers)

    def _collect_child_workflow(
        self,
        ref: ast_module.WorkflowRefDecl,
        source_dir: pathlib.Path,
        producers: dict[str, list[ArtifactRef]],
        consumers: list[ArtifactRef],
        diagnostics: list[diagnostics_module.Diagnostic],
    ) -> None:
        child_path = self._resolve_child_workflow(source_dir, ref.workflow_path)
        if child_path is None:
            return
        try:
            source = child_path.read_text(encoding="utf-8")
            child_ast = parser_module.Parser.from_text(source, source_name=str(child_path)).parse_workflow()
            validator_module.WorkflowValidator().validate(child_ast)
        except Exception as exc:
            diagnostics.append(
                diagnostics_module.Diagnostic(
                    f"Unable to inspect STEP WORKFLOW artifact contracts for {ref.workflow_path}: {exc}",
                    ref.location,
                    severity="error",
                    code="LGWF_ARTIFACT_CONTRACT_CHILD_ERROR",
                    suggestion="Fix the referenced child workflow so artifact contracts can be audited.",
                )
            )
            return
        self._collect_workflow(
            child_ast,
            child_path.parent,
            self._context_sets(child_ast),
            producers,
            consumers,
            diagnostics,
        )

    def _resolve_child_workflow(self, source_dir: pathlib.Path, raw_path: str) -> pathlib.Path | None:
        path = pathlib.Path(raw_path)
        if path.is_absolute() or ".." in path.parts:
            return None
        resolved = (source_dir / path).resolve()
        if not resolved.is_relative_to(self.package_root) or not resolved.is_file():
            return None
        return resolved

    def _add_producer(
        self,
        producers: dict[str, list[ArtifactRef]],
        raw_path: str,
        node_id: str,
        source: str,
        location: diagnostics_module.SourceLocation | None = None,
    ) -> None:
        path = self._artifact_path(raw_path)
        if path is None:
            return
        producers.setdefault(path, []).append(ArtifactRef(path, node_id, source, location))

    def _artifact_path(self, raw_path: str) -> str | None:
        normalized = raw_path.replace("\\", "/")
        parts = pathlib.PurePosixPath(normalized).parts
        if not parts or parts[0] != ".lgwf":
            return None
        return pathlib.PurePosixPath(*parts).as_posix()

    def _context_sets(self, ast: ast_module.WorkflowAst) -> dict[str, ast_module.ContextSetDecl]:
        return {
            statement.name: statement
            for statement in ast.statements
            if isinstance(statement, ast_module.ContextSetDecl)
        }

    def _expand_contexts(
        self,
        contexts: Iterable[ast_module.ContextRef],
        context_sets: dict[str, ast_module.ContextSetDecl],
    ) -> list[ast_module.ResourceRef]:
        resources: list[ast_module.ResourceRef] = []
        for context in contexts:
            if context.resource is not None:
                resources.append(context.resource)
            elif context.context_set is not None and context.context_set in context_sets:
                resources.extend(context_sets[context.context_set].resources)
        return resources

    def _source_dir_for_ast(self, ast: ast_module.WorkflowAst) -> pathlib.Path:
        if ast.source_name is not None:
            return pathlib.Path(ast.source_name).resolve().parent
        return self.package_root

    def _is_string_list(self, value: Any) -> bool:
        return isinstance(value, list) and all(isinstance(item, str) for item in value)

    def _invalid_contract(self, message: str) -> diagnostics_module.Diagnostic:
        return diagnostics_module.Diagnostic(
            message,
            None,
            severity="error",
            code="LGWF_ARTIFACT_CONTRACT_INVALID",
            suggestion=f"Fix {CONTRACT_FILE}; use bootstrap_inputs and script_writes with string paths.",
        )
