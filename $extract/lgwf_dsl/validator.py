import lgwf_dsl.ast as ast_module
import lgwf_dsl.catalog as catalog_module
import lgwf_dsl.diagnostics as diagnostics_module
import lgwf_dsl.errors as errors_module
import lgwf_client.tools.catalog as tool_catalog_module
import pathlib


class WorkflowValidator:
    def __init__(self, catalog: catalog_module.CapabilityCatalogView | None = None) -> None:
        self.catalog = catalog or catalog_module.CapabilityCatalogView.load_default()

    def validate(self, ast: ast_module.WorkflowAst) -> None:
        node_ids = self._node_ids(ast)
        context_sets = self._context_sets(ast)
        self._validate_runtime_capabilities(ast)
        self._validate_sandbox(ast.sandbox)
        self._validate_codex_output_paths(ast)

        if ast.entry_point not in node_ids:
            self._raise(f"Unknown entry_point: {ast.entry_point}", ast.location)

        for name, context_set in context_sets.items():
            if name in node_ids:
                self._raise(f"Context set name collides with node id: {name}", context_set.location)

        for statement in ast.statements:
            if isinstance(statement, ast_module.EdgeDecl):
                self._validate_node_ref(statement.from_node, node_ids, "edge source", statement.location)
                self._validate_node_ref(statement.to_node, node_ids, "edge target", statement.location)
            elif isinstance(statement, ast_module.FlowDecl):
                for node_id in statement.nodes:
                    self._validate_node_ref(node_id, node_ids, "flow", statement.location)
            elif isinstance(statement, ast_module.RouteDecl):
                self._validate_node_ref(statement.from_node, node_ids, "route source", statement.location)
                for target in statement.branches.values():
                    self._validate_node_ref(target, node_ids, "route target", statement.location)
            elif isinstance(statement, ast_module.CodexDecl):
                self._validate_context_refs(statement.contexts, context_sets)
            elif isinstance(statement, ast_module.ToolDecl):
                self._validate_tool(statement)
            elif isinstance(statement, ast_module.ReactDecl):
                self._validate_react_context_refs(statement, context_sets)
            elif isinstance(statement, ast_module.AgentLoopDecl):
                self._validate_agent_loop(statement, context_sets)
            elif isinstance(statement, ast_module.ParallelDecl):
                self._validate_parallel(statement, context_sets)

    def _validate_codex_output_paths(self, ast: ast_module.WorkflowAst) -> None:
        paths: dict[str, ast_module.CodexDecl] = {}
        for codex in self._codex_decls(ast):
            if codex.output_json_path is None:
                output_paths = []
            else:
                output_paths = [("CODEX OUTPUT_JSON path", codex.output_json_path)]
            output_paths.extend(("CODEX OUTPUT_FILE path", path) for path in codex.output_file_paths)
            for label, raw_path in output_paths:
                self._validate_relative_path(raw_path, label, codex.location)
                path = pathlib.PurePosixPath(raw_path.replace("\\", "/")).as_posix()
                if label == "CODEX OUTPUT_FILE path" and pathlib.PurePosixPath(path).suffix.lower() == ".json":
                    self._raise(
                        f"{label} must not reference a .json file; use OUTPUT_JSON for JSON artifacts.",
                        codex.location,
                    )
                existing = paths.get(path)
                if existing is not None:
                    self._raise(f"Duplicate CODEX output path: {path}", codex.location)
                paths[path] = codex

    def _codex_decls(self, ast: ast_module.WorkflowAst) -> list[ast_module.CodexDecl]:
        codex_decls: list[ast_module.CodexDecl] = []
        for statement in ast.statements:
            self._collect_codex_decls(statement, codex_decls)
        return codex_decls

    def _collect_codex_decls(self, statement: object, codex_decls: list[ast_module.CodexDecl]) -> None:
        if isinstance(statement, ast_module.CodexDecl):
            codex_decls.append(statement)
        elif isinstance(statement, ast_module.ReactDecl):
            for slot in statement.slots.values():
                self._collect_codex_decls(slot.task, codex_decls)
        elif isinstance(statement, ast_module.AgentLoopDecl):
            for slot in statement.slots.values():
                self._collect_codex_decls(slot.task, codex_decls)
        elif isinstance(statement, ast_module.ParallelDecl):
            for step in statement.steps:
                self._collect_codex_decls(step.task, codex_decls)

    def _node_ids(self, ast: ast_module.WorkflowAst) -> set[str]:
        node_ids: set[str] = set()
        for statement in ast.statements:
            if not isinstance(
                statement,
                (
                    ast_module.PythonDecl,
                    ast_module.ToolDecl,
                    ast_module.CodexDecl,
                    ast_module.ApprovalDecl,
                    ast_module.ReactDecl,
                    ast_module.AgentLoopDecl,
                    ast_module.WorkflowRefDecl,
                    ast_module.ParallelDecl,
                ),
            ):
                continue
            if statement.id in node_ids:
                self._raise(f"Duplicate node id: {statement.id}", statement.location)
            node_ids.add(statement.id)
        return node_ids

    def _context_sets(self, ast: ast_module.WorkflowAst) -> dict[str, ast_module.ContextSetDecl]:
        context_sets: dict[str, ast_module.ContextSetDecl] = {}
        for statement in ast.statements:
            if not isinstance(statement, ast_module.ContextSetDecl):
                continue
            if statement.name in context_sets:
                self._raise(f"Duplicate context set: {statement.name}", statement.location)
            context_sets[statement.name] = statement
        return context_sets

    def _validate_runtime_capabilities(self, ast: ast_module.WorkflowAst) -> None:
        for capability in (
            "exec.run_python",
            "exec.run_tool",
            "exec.codex_prompt",
            "flow.human_approval",
            "subgraph.agent_loop",
            "subgraph.react",
            "subgraph.parallel",
            "subgraph.workflow",
            "subgraph.validation_sandbox",
        ):
            self._validate_capability(capability, ast.location)

    def _validate_sandbox(self, sandbox: ast_module.SandboxDecl | None) -> None:
        if sandbox is None:
            return
        self._validate_relative_path(sandbox.path, "SANDBOX PATH", sandbox.location)
        self._validate_patterns(sandbox.work_dir.include, "WORK_DIR INCLUDE", sandbox.work_dir.location)
        self._validate_patterns(sandbox.work_dir.exclude, "WORK_DIR EXCLUDE", sandbox.work_dir.location)
        self._validate_patterns(
            sandbox.work_dir.promote_include,
            "WORK_DIR PROMOTE_INCLUDE",
            sandbox.work_dir.location,
        )
        if sandbox.target_dir is None:
            return
        if sandbox.target_dir.root != "workspace":
            self._raise("TARGET_DIR root must be workspace.", sandbox.target_dir.location)
        self._validate_relative_path(sandbox.target_dir.path, "TARGET_DIR path", sandbox.target_dir.location)
        self._validate_patterns(sandbox.target_dir.include, "TARGET_DIR INCLUDE", sandbox.target_dir.location)
        self._validate_patterns(sandbox.target_dir.exclude, "TARGET_DIR EXCLUDE", sandbox.target_dir.location)
        self._validate_patterns(
            sandbox.target_dir.promote_include,
            "TARGET_DIR PROMOTE_INCLUDE",
            sandbox.target_dir.location,
        )

    def _validate_patterns(
        self,
        patterns: list[str],
        label: str,
        location: diagnostics_module.SourceLocation | None,
    ) -> None:
        for pattern in patterns:
            self._validate_relative_path(pattern, label, location)

    def _validate_relative_path(
        self,
        raw_path: str,
        label: str,
        location: diagnostics_module.SourceLocation | None,
    ) -> None:
        path = pathlib.PurePosixPath(raw_path.replace("\\", "/"))
        if path.is_absolute():
            self._raise(f"{label} must be relative.", location)
        if ".." in path.parts:
            self._raise(f"{label} must not contain '..'.", location)

    def _validate_react_context_refs(
        self,
        react: ast_module.ReactDecl,
        context_sets: dict[str, ast_module.ContextSetDecl],
    ) -> None:
        for slot in react.slots.values():
            if isinstance(slot.task, ast_module.CodexDecl):
                self._validate_context_refs(slot.task.contexts, context_sets)
            elif isinstance(slot.task, ast_module.ToolDecl):
                self._validate_tool(slot.task)
            elif isinstance(slot.task, ast_module.WorkflowRefDecl) and slot.task.result_path is None:
                self._raise("REACT WORKFLOW requires RESULT state.*.", slot.task.location)

    def _validate_agent_loop(
        self,
        loop: ast_module.AgentLoopDecl,
        context_sets: dict[str, ast_module.ContextSetDecl],
    ) -> None:
        self._validate_relative_path(loop.artifacts_path, "AGENT_LOOP ARTIFACTS", loop.location)
        self._validate_context_refs(loop.contexts, context_sets)
        for slot in loop.slots.values():
            if isinstance(slot.task, ast_module.CodexDecl):
                self._validate_context_refs(slot.task.contexts, context_sets)
            elif isinstance(slot.task, ast_module.ToolDecl):
                self._validate_tool(slot.task)
            elif isinstance(slot.task, ast_module.WorkflowRefDecl) and slot.task.result_path is None:
                self._raise("AGENT_LOOP WORKFLOW requires RESULT state.*.", slot.task.location)

    def _validate_parallel(
        self,
        parallel: ast_module.ParallelDecl,
        context_sets: dict[str, ast_module.ContextSetDecl],
    ) -> None:
        step_ids: set[str] = set()
        result_paths: set[str] = set()
        for step in parallel.steps:
            if step.id in step_ids:
                self._raise(f"Duplicate PARALLEL step id: {step.id}", step.location)
            step_ids.add(step.id)
            if step.result_path.path in result_paths:
                self._raise(f"Duplicate PARALLEL result path: {step.result_path.path}", step.location)
            result_paths.add(step.result_path.path)
            if isinstance(step.task, ast_module.CodexDecl):
                self._validate_context_refs(step.task.contexts, context_sets)
            elif isinstance(step.task, ast_module.ToolDecl):
                self._validate_tool(step.task)
            elif isinstance(step.task, ast_module.ReactDecl):
                self._validate_react_context_refs(step.task, context_sets)

    def _validate_tool(self, tool: ast_module.ToolDecl) -> None:
        try:
            tool_catalog_module.validate_public_tool_options(tool.tool_name, tool.options)
        except tool_catalog_module.ToolCatalogError as exc:
            self._raise(
                str(exc),
                tool.location,
                code=exc.code,
                suggestion="Use a public tool and provide OPTIONS that match its catalog schema.",
            )

    def _validate_context_refs(
        self,
        contexts: list[ast_module.ContextRef],
        context_sets: dict[str, ast_module.ContextSetDecl],
    ) -> None:
        for context in contexts:
            if context.context_set is not None and context.context_set not in context_sets:
                self._raise(f"Unknown context set: {context.context_set}", context.location)

    def _validate_capability(
        self,
        capability: str,
        location: diagnostics_module.SourceLocation | None,
    ) -> None:
        if self.catalog.has_capability(capability):
            return
        suggestion = self.catalog.suggest_capability(capability)
        message = f"Unknown capability: {capability}"
        if suggestion:
            message = f"{message}. Did you mean '{suggestion}'?"
        self._raise(message, location)

    def _validate_node_ref(
        self,
        node_id: str,
        node_ids: set[str],
        label: str,
        location: diagnostics_module.SourceLocation | None,
    ) -> None:
        if node_id in node_ids:
            return
        self._raise(f"Unknown {label} node: {node_id}", location)

    def _raise(
        self,
        message: str,
        location: diagnostics_module.SourceLocation | None,
        *,
        code: str = "LGWF_DSL_ERROR",
        suggestion: str | None = None,
    ) -> None:
        raise errors_module.DSLValidationError(
            message,
            location,
            code=code,
            suggestion=suggestion,
        )
