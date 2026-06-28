import itertools
import pathlib
from typing import Any

import lgwf_dsl.ast as ast_module
import lgwf_dsl.parser as parser_module
import lgwf_dsl.validator as validator_module


class WorkflowLowerer:
    def lower(
        self,
        ast: ast_module.WorkflowAst,
        package_root: str | pathlib.Path | None = None,
    ) -> dict[str, Any]:
        previous_root = getattr(self, "_workflow_package_root", None)
        previous_source_dir = getattr(self, "_workflow_source_dir", None)
        previous_stack = getattr(self, "_workflow_ref_stack", None)
        if previous_root is None:
            self._workflow_package_root = self._resolve_package_root(ast.source_name, package_root)
            self._workflow_ref_stack = []
            if ast.source_name is not None:
                self._workflow_ref_stack.append(self._resolve_source_path(ast.source_name))
        elif package_root is not None and pathlib.Path(package_root).resolve() != previous_root:
            raise ValueError("Nested workflow compilation cannot change package_root.")
        self._workflow_source_dir = self._source_dir(ast.source_name)
        try:
            return self._lower_with_root(ast)
        finally:
            if previous_root is None:
                delattr(self, "_workflow_package_root")
                delattr(self, "_workflow_source_dir")
                delattr(self, "_workflow_ref_stack")
            else:
                self._workflow_package_root = previous_root
                self._workflow_source_dir = previous_source_dir
                self._workflow_ref_stack = previous_stack

    def _lower_with_root(self, ast: ast_module.WorkflowAst) -> dict[str, Any]:
        defaults = self._defaults(ast)
        context_sets = self._context_sets(ast)
        nodes = []
        edges = []
        routes = []

        for statement in ast.statements:
            if isinstance(statement, ast_module.PythonDecl):
                nodes.append(self._lower_python(statement, defaults))
            elif isinstance(statement, ast_module.ToolDecl):
                nodes.append(self._lower_tool(statement, defaults))
            elif isinstance(statement, ast_module.CodexDecl):
                nodes.append(self._lower_codex(statement, defaults, context_sets))
            elif isinstance(statement, ast_module.ApprovalDecl):
                nodes.append(self._lower_approval(statement, defaults))
            elif isinstance(statement, ast_module.ReactDecl):
                nodes.append(self._lower_react(statement, defaults, context_sets))
            elif isinstance(statement, ast_module.AgentLoopDecl):
                nodes.append(self._lower_agent_loop(statement, defaults, context_sets))
            elif isinstance(statement, ast_module.WorkflowRefDecl):
                nodes.append(self._lower_workflow_ref(statement))
            elif isinstance(statement, ast_module.ParallelDecl):
                nodes.append(self._lower_parallel(statement, defaults, context_sets))
            elif isinstance(statement, ast_module.EdgeDecl):
                edges.append([statement.from_node, statement.to_node])
            elif isinstance(statement, ast_module.FlowDecl):
                for from_node, to_node in itertools.pairwise(statement.nodes):
                    edges.append([from_node, to_node])
            elif isinstance(statement, ast_module.RouteDecl):
                routes.append({"from": statement.from_node, "branches": statement.branches})

        workflow = {
            "nodes": nodes,
            "edges": edges,
            "routes": routes,
            "entry_point": ast.entry_point,
        }
        if ast.sandbox is not None:
            return self._wrap_sandbox(ast, workflow)
        return workflow

    def _wrap_sandbox(self, ast: ast_module.WorkflowAst, workflow: dict[str, Any]) -> dict[str, Any]:
        sandbox = ast.sandbox
        if sandbox is None:
            return workflow
        sandbox_id = f"__sandbox__{ast.name or ast.entry_point}"
        config: dict[str, Any] = {
            "sandbox_path": sandbox.path,
            "work_dir": {
                "include": list(sandbox.work_dir.include),
                "exclude": list(sandbox.work_dir.exclude),
                "promote_include": list(sandbox.work_dir.promote_include),
            },
            "workflow": workflow,
        }
        if sandbox.target_dir is not None:
            config["target_dir"] = {
                "root": sandbox.target_dir.root,
                "path": sandbox.target_dir.path,
                "include": list(sandbox.target_dir.include),
                "exclude": list(sandbox.target_dir.exclude),
                "promote_include": list(sandbox.target_dir.promote_include),
            }
        if sandbox.result_path is not None:
            config["result_path"] = sandbox.result_path.path
        return {
            "nodes": [
                {
                    "id": sandbox_id,
                    "capability": "subgraph.validation_sandbox",
                    "config": config,
                }
            ],
            "edges": [],
            "routes": [],
            "entry_point": sandbox_id,
        }

    def _resolve_package_root(
        self,
        source_name: str | None,
        package_root: str | pathlib.Path | None,
    ) -> pathlib.Path:
        if package_root is not None:
            return pathlib.Path(package_root).resolve()
        if source_name is None:
            return pathlib.Path(".").resolve()
        return pathlib.Path(source_name).resolve().parent

    def _resolve_source_path(self, source_name: str) -> pathlib.Path:
        source_path = pathlib.Path(source_name)
        if source_path.is_absolute():
            return source_path.resolve()
        return (pathlib.Path(self._workflow_package_root) / source_path).resolve()

    def _source_dir(self, source_name: str | None) -> pathlib.Path:
        root = pathlib.Path(self._workflow_package_root).resolve()
        if source_name is None:
            return root
        source_path = self._resolve_source_path(source_name)
        if not source_path.is_relative_to(root):
            raise ValueError("Workflow source must stay within package_root.")
        return source_path.parent

    def _defaults(self, ast: ast_module.WorkflowAst) -> ast_module.DefaultsDecl:
        defaults = ast_module.DefaultsDecl()
        for statement in ast.statements:
            if isinstance(statement, ast_module.DefaultsDecl):
                defaults = statement
        return defaults

    def _context_sets(self, ast: ast_module.WorkflowAst) -> dict[str, ast_module.ContextSetDecl]:
        return {
            statement.name: statement
            for statement in ast.statements
            if isinstance(statement, ast_module.ContextSetDecl)
        }

    def _lower_python(self, task: ast_module.PythonDecl, defaults: ast_module.DefaultsDecl) -> dict[str, Any]:
        config = {
            "script_ref": {"path": self._lower_task_resource_path(task.script_path, "SCRIPT", defaults)},
            "timeout_seconds": self._resolve_timeout_seconds(
                task.timeout_seconds,
                task.timeout_unlimited,
                defaults.timeout_seconds,
                inherit_defaults=True,
            ),
            "instruction_path": self._state_path_or_default(task.instruction_path, defaults.instruction_path_template, task.id),
            "result_path": self._state_path_or_default(task.result_path, defaults.result_path_template, task.id),
            "ref_root": self._lower_ref_root(defaults.ref_root),
        }
        if task.updates_state:
            config["state_updates_from_stdout"] = True
        return {
            "id": task.id,
            "capability": "exec.run_python",
            "config": config,
        }

    def _lower_codex(
        self,
        task: ast_module.CodexDecl,
        defaults: ast_module.DefaultsDecl,
        context_sets: dict[str, ast_module.ContextSetDecl],
    ) -> dict[str, Any]:
        config = {
            "prompt_ref": {"path": self._lower_task_resource_path(task.prompt_path, "PROMPT", defaults)},
            "context_refs": self._lower_context_refs(task.contexts, context_sets),
            "timeout_seconds": self._resolve_timeout_seconds(
                task.timeout_seconds,
                task.timeout_unlimited,
                defaults.timeout_seconds,
                inherit_defaults=True,
            ),
            "instruction_path": self._state_path_or_default(task.instruction_path, defaults.instruction_path_template, task.id),
            "result_path": self._state_path_or_default(task.result_path, defaults.result_path_template, task.id),
            "ref_root": self._lower_ref_root(defaults.ref_root),
        }
        if task.target_dirs:
            config["target_dirs"] = list(task.target_dirs)
        if task.target_files:
            config["target_files"] = list(task.target_files)
        if task.target_dirs_path is not None:
            config["target_dirs_path"] = task.target_dirs_path.path
        if task.target_files_path is not None:
            config["target_files_path"] = task.target_files_path.path
        if task.output_json_path is not None:
            output_json_config = {
                "path": self._validate_relative_path(task.output_json_path, "OUTPUT_JSON").as_posix()
            }
            if task.output_json_mode is not None:
                if task.output_json_mode != "file":
                    raise ValueError("OUTPUT_JSON mode must be 'file'.")
                output_json_config["mode"] = task.output_json_mode
            config["output_json"] = output_json_config
        if task.output_file_paths:
            config["output_files"] = [
                self._validate_relative_path(path, "OUTPUT_FILE").as_posix()
                for path in task.output_file_paths
            ]
        return {
            "id": task.id,
            "capability": "exec.codex_prompt",
            "config": config,
        }

    def _lower_tool(self, task: ast_module.ToolDecl, defaults: ast_module.DefaultsDecl) -> dict[str, Any]:
        return {
            "id": task.id,
            "capability": "exec.run_tool",
            "config": {
                "tool": task.tool_name,
                "options": task.options,
                "timeout_seconds": self._resolve_timeout_seconds(
                    task.timeout_seconds,
                    task.timeout_unlimited,
                    defaults.timeout_seconds,
                    inherit_defaults=True,
                ),
                "result_path": self._state_path_or_default(
                    task.result_path,
                    defaults.result_path_template,
                    task.id,
                ),
            },
        }

    def _lower_approval(self, task: ast_module.ApprovalDecl, defaults: ast_module.DefaultsDecl) -> dict[str, Any]:
        config = {
            "context_path": task.read_path.path,
            "approved_value_path": task.write_path.path,
            "result_path": self._state_path_or_default(task.result_path, defaults.result_path_template, task.id),
            "timeout_seconds": self._resolve_timeout_seconds(
                task.timeout_seconds,
                task.timeout_unlimited,
                defaults.timeout_seconds,
                inherit_defaults=False,
            ),
        }
        if task.prompt is not None:
            config["prompt"] = task.prompt
        elif task.prompt_ref_path is not None:
            config["prompt_ref"] = {
                "root": "workflow",
                "path": self._package_relative_path(task.prompt_ref_path, "PROMPT_REF"),
            }
        if task.persist_path is not None:
            config["persist_value_path"] = task.persist_path
        if task.route_on_decision:
            config["route_on_decision"] = True
        if task.poll_interval_seconds is not None:
            config["poll_interval_seconds"] = task.poll_interval_seconds
        return {
            "id": task.id,
            "capability": "flow.human_approval",
            "config": config,
        }

    def _lower_react(
        self,
        react: ast_module.ReactDecl,
        defaults: ast_module.DefaultsDecl,
        context_sets: dict[str, ast_module.ContextSetDecl],
    ) -> dict[str, Any]:
        config: dict[str, Any] = {"max_steps": react.max_steps}
        if react.spec_path is not None:
            config["spec_ref"] = {
                "path": self._lower_task_resource_path(react.spec_path, "SPEC", defaults),
            }
        for slot_name in ("reason", "act", "observe", "decide"):
            task = react.slots[slot_name].task
            if isinstance(task, ast_module.PythonDecl):
                lowered = self._lower_python(task, defaults)
            elif isinstance(task, ast_module.ToolDecl):
                lowered = self._lower_tool(task, defaults)
            elif isinstance(task, ast_module.WorkflowRefDecl):
                lowered = self._lower_workflow_ref(task)
            else:
                lowered = self._lower_codex(task, defaults, context_sets)
            slot_data = {"capability": lowered["capability"]}
            if lowered.get("config"):
                slot_data["config"] = lowered["config"]
            config[slot_name] = slot_data
        if react.on_max_ask is not None:
            on_max = react.on_max_ask
            config["on_max"] = {
                "type": "human_approval",
                "prompt": on_max.prompt,
                "context_path": on_max.read_path.path,
                "approved_value_path": on_max.write_path.path,
                "result_path": self._state_path_or_default(
                    on_max.result_path,
                    defaults.result_path_template,
                    f"{react.id}__on_max",
                ),
                "status_path": self._state_path_or_default(
                    on_max.status_path,
                    "react.{node}",
                    react.id,
                ),
                "extra_max_steps": on_max.extra_max_steps,
                "poll_interval_seconds": on_max.poll_interval_seconds or 1,
                "timeout_seconds": self._resolve_timeout_seconds(
                    on_max.timeout_seconds,
                    on_max.timeout_unlimited,
                    defaults.timeout_seconds,
                    inherit_defaults=False,
                ),
            }
        return {
            "id": react.id,
            "capability": "subgraph.react",
            "config": config,
        }

    def _lower_agent_loop(
        self,
        loop: ast_module.AgentLoopDecl,
        defaults: ast_module.DefaultsDecl,
        context_sets: dict[str, ast_module.ContextSetDecl],
    ) -> dict[str, Any]:
        loop_context_refs = self._lower_context_refs(loop.contexts, context_sets)
        config: dict[str, Any] = {
            "max_iterations": loop.max_iterations,
            "artifacts_path": loop.artifacts_path,
            "status_path": self._state_path_or_default(loop.status_path, "agent_loop.{node}.status", loop.id),
            "report_path": self._state_path_or_default(loop.report_path, "agent_loop.{node}.report", loop.id),
            "target_dirs_path": "targets.dirs",
            "target_files_path": "targets.files",
            "goal": loop.goal,
            "slot_order": list(loop.slot_order),
            "on_max": loop.on_max,
            "on_error": loop.on_error,
            "token_max": loop.token_max,
        }
        for slot_name in loop.slot_order:
            lowered = self._lower_agent_loop_slot_task(
                loop.slots[slot_name].task,
                defaults,
                context_sets,
                loop_context_refs,
            )
            slot_data = {"capability": lowered["capability"]}
            if lowered.get("config"):
                slot_data["config"] = lowered["config"]
            config[slot_name] = slot_data
        return {
            "id": loop.id,
            "capability": "subgraph.agent_loop",
            "config": config,
        }

    def _lower_agent_loop_slot_task(
        self,
        task: ast_module.PythonDecl | ast_module.ToolDecl | ast_module.CodexDecl | ast_module.WorkflowRefDecl,
        defaults: ast_module.DefaultsDecl,
        context_sets: dict[str, ast_module.ContextSetDecl],
        loop_context_refs: list[dict[str, str]],
    ) -> dict[str, Any]:
        if isinstance(task, ast_module.PythonDecl):
            return self._lower_python(task, defaults)
        if isinstance(task, ast_module.ToolDecl):
            return self._lower_tool(task, defaults)
        if isinstance(task, ast_module.WorkflowRefDecl):
            return self._lower_workflow_ref(task)

        lowered = self._lower_codex(task, defaults, context_sets)
        config = dict(lowered.get("config", {}))
        slot_context_refs = list(config.get("context_refs", []))
        config["context_refs"] = [*loop_context_refs, *slot_context_refs]
        config["target_dirs_path"] = "targets.dirs"
        config["target_files_path"] = "targets.files"
        return {
            "id": lowered["id"],
            "capability": lowered["capability"],
            "config": config,
        }

    def _lower_parallel(
        self,
        parallel: ast_module.ParallelDecl,
        defaults: ast_module.DefaultsDecl,
        context_sets: dict[str, ast_module.ContextSetDecl],
    ) -> dict[str, Any]:
        config: dict[str, Any] = {
            "steps": [
                self._lower_parallel_step(step, defaults, context_sets)
                for step in parallel.steps
            ]
        }
        if parallel.max_concurrency is not None:
            config["max_concurrency"] = parallel.max_concurrency
        if parallel.fail_strategy is not None:
            config["fail_strategy"] = parallel.fail_strategy
        return {
            "id": parallel.id,
            "capability": "subgraph.parallel",
            "config": config,
        }

    def _lower_parallel_step(
        self,
        step: ast_module.ParallelStepDecl,
        defaults: ast_module.DefaultsDecl,
        context_sets: dict[str, ast_module.ContextSetDecl],
    ) -> dict[str, Any]:
        if isinstance(step.task, ast_module.PythonDecl):
            lowered = self._lower_python(step.task, defaults)
        elif isinstance(step.task, ast_module.ToolDecl):
            lowered = self._lower_tool(step.task, defaults)
        elif isinstance(step.task, ast_module.CodexDecl):
            lowered = self._lower_codex(step.task, defaults, context_sets)
        else:
            if isinstance(step.task, ast_module.WorkflowRefDecl):
                lowered = self._lower_workflow_ref(step.task)
            else:
                lowered = self._lower_react(step.task, defaults, context_sets)

        result = {
            "id": step.id,
            "capability": lowered["capability"],
            "output_path": step.output_path.path,
            "result_path": step.result_path.path,
        }
        if lowered.get("config"):
            result["config"] = lowered["config"]
        return result

    def _lower_workflow_ref(
        self,
        ref: ast_module.WorkflowRefDecl,
    ) -> dict[str, Any]:
        source_path = self._resolve_workflow_ref(ref.workflow_path)
        stack = self._workflow_ref_stack
        if source_path in stack:
            cycle_start = stack.index(source_path)
            cycle = stack[cycle_start:] + [source_path]
            chain = " -> ".join(self._display_workflow_path(path) for path in cycle)
            raise ValueError(f"Workflow reference cycle: {chain}")

        text = source_path.read_text(encoding="utf-8")
        ast = parser_module.Parser.from_text(text, source_name=str(source_path)).parse_workflow()
        validator_module.WorkflowValidator().validate(ast)
        stack.append(source_path)
        try:
            workflow = self.lower(ast)
        finally:
            stack.pop()
        config: dict[str, Any] = {"workflow": workflow}
        if ref.result_path is not None:
            config["result_path"] = ref.result_path.path
        return {
            "id": ref.id,
            "capability": "subgraph.workflow",
            "config": config,
        }

    def _resolve_workflow_ref(self, workflow_path: str) -> pathlib.Path:
        ref_path = pathlib.Path(workflow_path)
        if ref_path.is_absolute() or ".." in ref_path.parts:
            raise ValueError("STEP WORKFLOW path must be relative and must not contain '..'.")
        if ref_path.suffix.lower() != ".lgwf":
            raise ValueError("STEP WORKFLOW path must reference a .lgwf file.")
        root = getattr(self, "_workflow_package_root", None)
        if root is None:
            root = pathlib.Path(".").resolve()
        root = pathlib.Path(root).resolve()
        source_path = (pathlib.Path(self._workflow_source_dir) / ref_path).resolve()
        if not source_path.is_relative_to(root):
            raise ValueError("STEP WORKFLOW path must stay within the workflow package root.")
        if not source_path.is_file():
            raise FileNotFoundError(f"Referenced workflow not found: {source_path}")
        return source_path

    def _display_workflow_path(self, path: pathlib.Path) -> str:
        root = pathlib.Path(self._workflow_package_root).resolve()
        try:
            return path.relative_to(root).as_posix()
        except ValueError:
            return str(path)

    def _lower_context_refs(
        self,
        contexts: list[ast_module.ContextRef],
        context_sets: dict[str, ast_module.ContextSetDecl],
    ) -> list[dict[str, str]]:
        refs = []
        for context in contexts:
            if context.resource is not None:
                refs.append(self._lower_resource_ref(context.resource))
            elif context.context_set is not None:
                for resource in context_sets[context.context_set].resources:
                    refs.append(self._lower_resource_ref(resource))
        return refs

    def _lower_resource_ref(self, resource: ast_module.ResourceRef) -> dict[str, str]:
        path = resource.path
        if resource.root == "workflow":
            path = self._package_relative_path(resource.path, "CONTEXT workflow")
        else:
            self._validate_relative_path(resource.path, "CONTEXT workspace")
        return {
            "root": resource.root,
            "path": path,
            "type": resource.type,
        }

    def _lower_task_resource_path(
        self,
        raw_path: str,
        label: str,
        defaults: ast_module.DefaultsDecl,
    ) -> str:
        root_name = defaults.ref_root.get("root")
        if root_name == "workspace":
            self._validate_relative_path(defaults.ref_root.get("path", "."), "ref_root")
            self._validate_relative_path(raw_path, label)
            return raw_path
        if root_name != "workflow":
            raise ValueError("ref_root.root must be one of: workflow, workspace.")

        ref_root_path = defaults.ref_root.get("path", ".")
        self._validate_relative_path(ref_root_path, "ref_root")
        base_dir = (pathlib.Path(self._workflow_source_dir) / ref_root_path).resolve()
        return self._package_relative_path(raw_path, label, base_dir=base_dir)

    def _lower_ref_root(self, ref_root: dict[str, str]) -> dict[str, str]:
        if ref_root.get("root") == "workflow":
            return {"root": "workflow", "path": "."}
        return dict(ref_root)

    def _package_relative_path(
        self,
        raw_path: str,
        label: str,
        base_dir: pathlib.Path | None = None,
    ) -> str:
        path = self._validate_relative_path(raw_path, label)
        root = pathlib.Path(self._workflow_package_root).resolve()
        base = pathlib.Path(base_dir or self._workflow_source_dir).resolve()
        resolved = (base / path).resolve()
        if not resolved.is_relative_to(root):
            raise ValueError(f"{label} path must stay within the workflow package root.")
        return resolved.relative_to(root).as_posix()

    def _validate_relative_path(self, raw_path: str, label: str) -> pathlib.Path:
        path = pathlib.Path(raw_path)
        if path.is_absolute():
            raise ValueError(f"{label} path must be relative.")
        if ".." in path.parts:
            raise ValueError(f"{label} path must not contain '..'.")
        return path

    def _state_path_or_default(
        self,
        state_ref: ast_module.StateRef | None,
        template: str,
        node_id: str,
    ) -> str:
        if state_ref is not None:
            return state_ref.path
        return template.replace("{node}", node_id)

    def _resolve_timeout_seconds(
        self,
        task_timeout: int | None,
        task_unlimited: bool,
        defaults_timeout: int,
        *,
        inherit_defaults: bool,
    ) -> int | None:
        if task_unlimited:
            return None
        if task_timeout is not None:
            return task_timeout
        if inherit_defaults:
            return defaults_timeout
        return None
