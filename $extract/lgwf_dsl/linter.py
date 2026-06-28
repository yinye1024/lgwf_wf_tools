from collections.abc import Iterable
import pathlib
from pathlib import PurePosixPath

import lgwf_dsl.ast as ast_module
import lgwf_dsl.diagnostics as diagnostics_module
import lgwf_dsl.parser as parser_module
import lgwf_dsl.validator as validator_module


class WorkflowLinter:
    """Authoring-time checks for workflow contracts that are legal but risky."""

    def __init__(self, package_root: str | pathlib.Path | None = None) -> None:
        self.package_root = pathlib.Path(package_root).resolve() if package_root is not None else None
        self._visited_workflows: set[pathlib.Path] = set()

    def lint(self, ast: ast_module.WorkflowAst) -> list[diagnostics_module.Diagnostic]:
        previous_source_dir = getattr(self, "_current_source_dir", None)
        self._current_source_dir = self._source_dir_for_ast(ast)
        source_path = pathlib.Path(ast.source_name).expanduser().resolve() if ast.source_name is not None else None
        if source_path is not None and source_path in self._visited_workflows:
            return []
        if source_path is not None:
            self._visited_workflows.add(source_path)
        try:
            context_sets = self._context_sets(ast)
            diagnostics: list[diagnostics_module.Diagnostic] = []
            diagnostics.extend(self._lint_authoring_resources(ast, context_sets))
            for statement in ast.statements:
                if isinstance(statement, ast_module.ReactDecl):
                    diagnostics.extend(self._lint_react_observe_scope(statement, context_sets))
                elif isinstance(statement, ast_module.ParallelDecl):
                    diagnostics.extend(self._lint_parallel_contexts(statement, context_sets))
            return diagnostics
        finally:
            self._current_source_dir = previous_source_dir

    def _lint_authoring_resources(
        self,
        ast: ast_module.WorkflowAst,
        context_sets: dict[str, ast_module.ContextSetDecl],
    ) -> list[diagnostics_module.Diagnostic]:
        if ast.source_name is None and self.package_root is None:
            return []

        defaults = self._defaults(ast)
        diagnostics: list[diagnostics_module.Diagnostic] = []
        for statement in ast.statements:
            diagnostics.extend(self._lint_statement_resources(statement, defaults, context_sets))
        return diagnostics

    def _lint_statement_resources(
        self,
        statement: ast_module.StatementDecl,
        defaults: ast_module.DefaultsDecl,
        context_sets: dict[str, ast_module.ContextSetDecl],
    ) -> list[diagnostics_module.Diagnostic]:
        if isinstance(statement, ast_module.PythonDecl):
            missing = self._missing_task_resource(statement.script_path, "SCRIPT", defaults, statement.location)
            return [missing] if missing is not None else []
        if isinstance(statement, ast_module.CodexDecl):
            diagnostics = [self._missing_task_resource(statement.prompt_path, "PROMPT", defaults, statement.location)]
            diagnostics.extend(self._lint_context_resources(statement.contexts, context_sets))
            return [diagnostic for diagnostic in diagnostics if diagnostic is not None]
        if isinstance(statement, ast_module.ApprovalDecl) and statement.prompt_ref_path is not None:
            missing = self._missing_workflow_resource(
                statement.prompt_ref_path,
                "PROMPT_REF",
                statement.location,
            )
            return [missing] if missing is not None else []
        if isinstance(statement, ast_module.ReactDecl):
            diagnostics: list[diagnostics_module.Diagnostic] = []
            if statement.spec_path is not None:
                missing = self._missing_task_resource(
                    statement.spec_path,
                    "SPEC",
                    defaults,
                    statement.location,
                )
                if missing is not None:
                    diagnostics.append(missing)
            for slot in statement.slots.values():
                diagnostics.extend(self._lint_statement_resources(slot.task, defaults, context_sets))
            return diagnostics
        if isinstance(statement, ast_module.AgentLoopDecl):
            diagnostics = []
            diagnostics.extend(self._lint_context_resources(statement.contexts, context_sets))
            for slot in statement.slots.values():
                diagnostics.extend(self._lint_statement_resources(slot.task, defaults, context_sets))
            return diagnostics
        if isinstance(statement, ast_module.WorkflowRefDecl):
            missing = self._missing_workflow_ref(statement.workflow_path, statement.location)
            if missing is not None:
                return [missing]
            return self._lint_child_workflow(statement)
        if isinstance(statement, ast_module.ParallelDecl):
            diagnostics = []
            for step in statement.steps:
                diagnostics.extend(self._lint_statement_resources(step.task, defaults, context_sets))
            return diagnostics
        return []

    def _lint_context_resources(
        self,
        contexts: Iterable[ast_module.ContextRef],
        context_sets: dict[str, ast_module.ContextSetDecl],
    ) -> list[diagnostics_module.Diagnostic]:
        diagnostics: list[diagnostics_module.Diagnostic] = []
        for context in contexts:
            resources: list[ast_module.ResourceRef] = []
            if context.resource is not None:
                resources.append(context.resource)
            elif context.context_set is not None and context.context_set in context_sets:
                resources.extend(context_sets[context.context_set].resources)
            for resource in resources:
                if resource.root != "workflow":
                    continue
                missing = self._missing_workflow_resource(resource.path, f"CONTEXT workflow {resource.type}", resource.location)
                if missing is not None:
                    diagnostics.append(missing)
        return diagnostics

    def _defaults(self, ast: ast_module.WorkflowAst) -> ast_module.DefaultsDecl:
        defaults = ast_module.DefaultsDecl()
        for statement in ast.statements:
            if isinstance(statement, ast_module.DefaultsDecl):
                defaults = statement
        return defaults

    def _missing_task_resource(
        self,
        raw_path: str,
        label: str,
        defaults: ast_module.DefaultsDecl,
        location: diagnostics_module.SourceLocation | None,
    ) -> diagnostics_module.Diagnostic | None:
        root = defaults.ref_root.get("root", "workflow")
        if root != "workflow":
            return None
        ref_root_path = defaults.ref_root.get("path", ".")
        base_dir = self._source_dir()
        if base_dir is None:
            return None
        resolved_base = self._resolve_relative(base_dir, ref_root_path)
        if resolved_base is None:
            return self._resource_diagnostic(ref_root_path, "ref_root", location, "ref_root path must be relative and stay inside the workflow package.")
        resolved = self._resolve_relative(resolved_base, raw_path)
        if resolved is None or not resolved.is_file():
            return self._resource_diagnostic(raw_path, label, location, f"Create the {label} file or update its path to an existing workflow package file.")
        return None

    def _missing_workflow_resource(
        self,
        raw_path: str,
        label: str,
        location: diagnostics_module.SourceLocation | None,
    ) -> diagnostics_module.Diagnostic | None:
        base_dir = self._source_dir()
        if base_dir is None:
            return None
        resolved = self._resolve_relative(base_dir, raw_path)
        if resolved is None:
            return self._resource_diagnostic(raw_path, label, location, "Use a relative path inside the workflow package.")
        if not resolved.exists():
            return self._resource_diagnostic(raw_path, label, location, f"Create the referenced {label} resource or update the path.")
        return None

    def _missing_workflow_ref(
        self,
        raw_path: str,
        location: diagnostics_module.SourceLocation | None,
    ) -> diagnostics_module.Diagnostic | None:
        base_dir = self._source_dir()
        if base_dir is None:
            return None
        resolved = self._resolve_relative(base_dir, raw_path)
        if resolved is None or pathlib.PurePath(raw_path).suffix.lower() != ".lgwf" or not resolved.is_file():
            return self._resource_diagnostic(raw_path, "STEP WORKFLOW", location, "Point STEP WORKFLOW at an existing relative .lgwf file inside the workflow package.")
        return None

    def _resolve_relative(self, base_dir: pathlib.Path, raw_path: str) -> pathlib.Path | None:
        path = pathlib.Path(raw_path)
        if path.is_absolute() or ".." in path.parts:
            return None
        resolved = (base_dir / path).resolve()
        if self.package_root is not None and not resolved.is_relative_to(self.package_root):
            return None
        return resolved

    def _source_dir(self) -> pathlib.Path | None:
        return getattr(self, "_current_source_dir", None)

    def _source_dir_for_ast(self, ast: ast_module.WorkflowAst) -> pathlib.Path | None:
        if self.package_root is None:
            return None
        if ast.source_name is not None:
            return pathlib.Path(ast.source_name).expanduser().resolve().parent
        return self.package_root

    def _lint_child_workflow(self, ref: ast_module.WorkflowRefDecl) -> list[diagnostics_module.Diagnostic]:
        base_dir = self._source_dir()
        if base_dir is None:
            return []
        child_path = self._resolve_relative(base_dir, ref.workflow_path)
        if child_path is None or not child_path.is_file():
            return []
        source = child_path.read_text(encoding="utf-8")
        child_ast = parser_module.Parser.from_text(source, source_name=str(child_path)).parse_workflow()
        validator_module.WorkflowValidator().validate(child_ast)
        return self.lint(child_ast)

    def _resource_diagnostic(
        self,
        raw_path: str,
        label: str,
        location: diagnostics_module.SourceLocation | None,
        suggestion: str,
    ) -> diagnostics_module.Diagnostic:
        return diagnostics_module.Diagnostic(
            f"{label} resource not found or invalid: {raw_path}",
            location,
            severity="error",
            code="LGWF_RESOURCE_MISSING",
            suggestion=suggestion,
        )

    def _lint_parallel_contexts(
        self,
        parallel: ast_module.ParallelDecl,
        context_sets: dict[str, ast_module.ContextSetDecl],
    ) -> list[diagnostics_module.Diagnostic]:
        diagnostics: list[diagnostics_module.Diagnostic] = []
        for step in parallel.steps:
            codex_tasks = self._codex_tasks(step.task)
            if codex_tasks and not any(self._has_explicit_codex_scope(task) for task in codex_tasks):
                diagnostics.append(
                    diagnostics_module.Diagnostic(
                        f"PARALLEL {parallel.id} step {step.id} has no CODEX context_refs or targets; parallel steps should organize context through files, explicit refs, or analysis targets.",
                        step.location or parallel.location,
                    )
                )
            if isinstance(step.task, ast_module.ReactDecl):
                diagnostics.extend(self._lint_react_observe_scope(step.task, context_sets))
        return diagnostics

    def _codex_tasks(
        self,
        task: ast_module.PythonDecl | ast_module.ToolDecl | ast_module.CodexDecl | ast_module.ReactDecl,
    ) -> list[ast_module.CodexDecl]:
        if isinstance(task, ast_module.CodexDecl):
            return [task]
        if isinstance(task, ast_module.ReactDecl):
            return [
                slot.task
                for slot in task.slots.values()
                if isinstance(slot.task, ast_module.CodexDecl)
            ]
        return []

    def _has_explicit_codex_scope(self, task: ast_module.CodexDecl) -> bool:
        return bool(
            task.contexts
            or task.target_dirs
            or task.target_files
            or task.target_dirs_path is not None
            or task.target_files_path is not None
        )

    def _lint_react_observe_scope(
        self,
        react: ast_module.ReactDecl,
        context_sets: dict[str, ast_module.ContextSetDecl],
    ) -> list[diagnostics_module.Diagnostic]:
        observe_slot = react.slots.get("observe")
        if observe_slot is None or not isinstance(observe_slot.task, ast_module.CodexDecl):
            return []

        observed_paths = {
            self._normalize_path(resource.path)
            for resource in self._expand_contexts(observe_slot.task.contexts, context_sets)
            if resource.type == "file"
        }

        required_paths: set[str] = set()
        for slot_name in ("reason", "act"):
            slot = react.slots.get(slot_name)
            if slot is None or not isinstance(slot.task, ast_module.CodexDecl):
                continue
            for resource in self._expand_contexts(slot.task.contexts, context_sets):
                path = self._normalize_path(resource.path)
                if self._is_factual_data_file(resource.type, path):
                    required_paths.add(path)

        missing_paths = sorted(required_paths - observed_paths)
        if not missing_paths:
            return []

        missing_text = ", ".join(missing_paths)
        return [
            diagnostics_module.Diagnostic(
                f"REACT {react.id} observe context_refs missing input file used by reason/act: {missing_text}",
                observe_slot.location or react.location,
            )
        ]

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

    def _is_factual_data_file(self, resource_type: str, path: str) -> bool:
        parsed = PurePosixPath(path)
        return resource_type == "file" and parsed.parts[:1] == ("data",) and parsed.suffix in {".json", ".md"}

    def _normalize_path(self, path: str) -> str:
        return path.replace("\\", "/")
