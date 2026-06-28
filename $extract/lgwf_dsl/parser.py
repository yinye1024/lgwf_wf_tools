import json
import math

import lgwf_dsl.ast as ast_module
import lgwf_dsl.errors as errors_module
import lgwf_dsl.lexer as lexer_module
import lgwf_dsl.tokens as tokens_module


class Parser:
    REACT_SLOTS = ("reason", "act", "observe", "decide")
    AGENT_LOOP_SLOTS = ("observe", "diagnose", "plan", "act", "verify", "decide")
    TOP_LEVEL_STATEMENTS = (
        "DEFAULTS",
        "CONTEXT_SET",
        "SANDBOX",
        "PY",
        "TOOL",
        "CODEX",
        "APPROVAL",
        "REACT",
        "AGENT_LOOP",
        "STEP",
        "PARALLEL",
        "EDGE",
        "FLOW",
        "ROUTE",
    )

    def __init__(
        self,
        text: str,
        tokens: list[tokens_module.Token],
        source_name: str | None = None,
    ) -> None:
        self.text = text
        self.tokens = tokens
        self.source_name = source_name
        self.index = 0
        self.lexer = lexer_module.Lexer(text, source_name)

    @classmethod
    def from_text(cls, text: str, source_name: str | None = None) -> "Parser":
        lexer = lexer_module.Lexer(text, source_name)
        return cls(text, lexer.tokenize(), source_name)

    def parse_workflow(self) -> ast_module.WorkflowAst:
        workflow_token = self._expect_keyword("WORKFLOW")
        name = self._expect_identifier("workflow name")
        self._expect_symbol(";")

        sandbox: ast_module.SandboxDecl | None = None
        while self._matches_keyword("SANDBOX"):
            if sandbox is not None:
                raise errors_module.DSLParseError("Duplicate SANDBOX declaration.", self._peek().location)
            sandbox = self._parse_sandbox()

        self._expect_keyword("ENTRY")
        entry_point = self._expect_identifier("entry point")
        self._expect_symbol(";")

        statements: list[ast_module.StatementDecl] = []
        while not self._is_eof():
            if self._matches_keyword("DEFAULTS"):
                statements.append(self._parse_defaults())
            elif self._matches_keyword("CONTEXT_SET"):
                statements.append(self._parse_context_set())
            elif self._matches_keyword("PY"):
                statements.append(self._parse_python())
            elif self._matches_keyword("TOOL"):
                statements.append(self._parse_tool())
            elif self._matches_keyword("CODEX"):
                statements.append(self._parse_codex())
            elif self._matches_keyword("APPROVAL"):
                statements.append(self._parse_approval())
            elif self._matches_keyword("REACT"):
                statements.append(self._parse_react())
            elif self._matches_keyword("AGENT_LOOP"):
                statements.append(self._parse_agent_loop())
            elif self._matches_keyword("STEP"):
                statements.append(self._parse_workflow_ref())
            elif self._matches_keyword("PARALLEL"):
                statements.append(self._parse_parallel())
            elif self._matches_keyword("EDGE"):
                statements.append(self._parse_edge())
            elif self._matches_keyword("FLOW"):
                flow_statement = self._parse_flow()
                if isinstance(flow_statement, list):
                    statements.extend(flow_statement)
                else:
                    statements.append(flow_statement)
            elif self._matches_keyword("ROUTE"):
                statements.append(self._parse_route())
            elif self._matches_keyword("SANDBOX"):
                raise errors_module.DSLParseError(
                    "SANDBOX must appear before ENTRY.",
                    self._peek().location,
                )
            elif self._matches_keyword("NODE"):
                raise errors_module.DSLParseError(
                    "NODE syntax is not supported in Authoring DSL v2. Use PY, CODEX, APPROVAL, or REACT.",
                    self._peek().location,
                )
            elif self._matches_keyword("CONFIG"):
                raise errors_module.DSLParseError(
                    "CONFIG JSON blocks are not supported in Authoring DSL v2.",
                    self._peek().location,
                )
            elif self._matches_keyword("WATERFALL"):
                raise errors_module.DSLParseError(
                    "WATERFALL syntax is not supported in Authoring DSL v2.",
                    self._peek().location,
                )
            else:
                token = self._peek()
                allowed = ", ".join(self.TOP_LEVEL_STATEMENTS)
                raise errors_module.DSLParseError(
                    f"Unexpected token: {token.value}. Allowed top-level statements: {allowed}.",
                    token.location,
                )

        return ast_module.WorkflowAst(
            name=name,
            entry_point=entry_point,
            statements=statements,
            sandbox=sandbox,
            location=workflow_token.location,
            source_name=self.source_name,
        )

    def _parse_sandbox(self) -> ast_module.SandboxDecl:
        start = self._expect_keyword("SANDBOX")
        self._expect_symbol("{")
        sandbox_path: str | None = None
        work_dir: ast_module.SandboxRootDecl | None = None
        target_dir: ast_module.SandboxTargetDirDecl | None = None
        result_path: ast_module.StateRef | None = None
        seen: set[str] = set()
        while not self._matches_symbol("}"):
            field = self._peek().value.upper()
            if field in seen and field in {"PATH", "WORK_DIR", "TARGET_DIR", "RESULT"}:
                raise errors_module.DSLParseError(f"Duplicate SANDBOX field: {field}.", self._peek().location)
            seen.add(field)
            if self._matches_keyword("PATH"):
                self._advance()
                sandbox_path = self._expect_string("SANDBOX PATH")
            elif self._matches_keyword("WORK_DIR"):
                work_dir = self._parse_sandbox_work_dir()
            elif self._matches_keyword("TARGET_DIR"):
                target_dir = self._parse_sandbox_target_dir()
            elif self._matches_keyword("RESULT"):
                self._advance()
                result_path = self._expect_state_ref("SANDBOX RESULT")
            else:
                raise errors_module.DSLParseError(
                    f"Unexpected SANDBOX token: {self._peek().value}",
                    self._peek().location,
                )
        self._expect_symbol("}")
        self._consume_optional_semicolon()
        if sandbox_path is None:
            raise errors_module.DSLParseError("SANDBOX requires PATH.", start.location)
        if work_dir is None:
            raise errors_module.DSLParseError("SANDBOX requires WORK_DIR.", start.location)
        return ast_module.SandboxDecl(
            path=sandbox_path,
            work_dir=work_dir,
            target_dir=target_dir,
            result_path=result_path,
            location=start.location,
        )

    def _parse_sandbox_work_dir(self) -> ast_module.SandboxRootDecl:
        start = self._expect_keyword("WORK_DIR")
        include, exclude, promote_include = self._parse_sandbox_root_patterns("WORK_DIR")
        return ast_module.SandboxRootDecl(
            include=include,
            exclude=exclude,
            promote_include=promote_include,
            location=start.location,
        )

    def _parse_sandbox_target_dir(self) -> ast_module.SandboxTargetDirDecl:
        start = self._expect_keyword("TARGET_DIR")
        root = self._expect_identifier("TARGET_DIR root").lower()
        path = self._expect_string("TARGET_DIR path")
        include, exclude, promote_include = self._parse_sandbox_root_patterns("TARGET_DIR")
        return ast_module.SandboxTargetDirDecl(
            root=root,
            path=path,
            include=include,
            exclude=exclude,
            promote_include=promote_include,
            location=start.location,
        )

    def _parse_sandbox_root_patterns(self, label: str) -> tuple[list[str], list[str], list[str]]:
        self._expect_symbol("{")
        include: list[str] = []
        exclude: list[str] = []
        promote_include: list[str] = []
        while not self._matches_symbol("}"):
            if self._matches_keyword("INCLUDE"):
                self._advance()
                include.append(self._expect_string(f"{label} INCLUDE"))
            elif self._matches_keyword("EXCLUDE"):
                self._advance()
                exclude.append(self._expect_string(f"{label} EXCLUDE"))
            elif self._matches_keyword("PROMOTE_INCLUDE"):
                self._advance()
                promote_include.append(self._expect_string(f"{label} PROMOTE_INCLUDE"))
            else:
                raise errors_module.DSLParseError(
                    f"Unexpected {label} token: {self._peek().value}",
                    self._peek().location,
                )
        self._expect_symbol("}")
        if not include:
            raise errors_module.DSLParseError(f"{label} requires at least one INCLUDE.", self._peek().location)
        if not promote_include:
            raise errors_module.DSLParseError(
                f"{label} requires at least one PROMOTE_INCLUDE.",
                self._peek().location,
            )
        return include, exclude, promote_include

    def _parse_workflow_ref(self) -> ast_module.WorkflowRefDecl:
        start = self._expect_keyword("STEP")
        step_id = self._expect_identifier("step id")
        self._expect_keyword("WORKFLOW")
        workflow_path = self._expect_string("WORKFLOW path")
        self._expect_symbol(";")
        return ast_module.WorkflowRefDecl(
            id=step_id,
            workflow_path=workflow_path,
            location=start.location,
        )

    def _parse_defaults(self) -> ast_module.DefaultsDecl:
        start = self._expect_keyword("DEFAULTS")
        self._expect_symbol("{")
        ref_root = {"root": "workflow", "path": "."}
        timeout_seconds = 300
        instruction_template = "instructions.{node}"
        result_template = "results.{node}"
        while not self._matches_symbol("}"):
            if self._matches_keyword("ref_root"):
                self._advance()
                root = self._expect_identifier("ref_root root")
                path = self._expect_string("ref_root path")
                ref_root = {"root": root, "path": path}
            elif self._matches_keyword("timeout_seconds"):
                self._advance()
                timeout_seconds = self._expect_positive_int("timeout_seconds")
            elif self._matches_keyword("instruction_path"):
                self._advance()
                instruction_template = self._expect_string("instruction_path template")
            elif self._matches_keyword("result_path"):
                self._advance()
                result_template = self._expect_string("result_path template")
            else:
                raise errors_module.DSLParseError(
                    f"Unexpected DEFAULTS token: {self._peek().value}",
                    self._peek().location,
                )
            self._expect_symbol(";")
        self._expect_symbol("}")
        self._consume_optional_semicolon()
        return ast_module.DefaultsDecl(
            ref_root=ref_root,
            timeout_seconds=timeout_seconds,
            instruction_path_template=instruction_template,
            result_path_template=result_template,
            location=start.location,
        )

    def _parse_context_set(self) -> ast_module.ContextSetDecl:
        start = self._expect_keyword("CONTEXT_SET")
        name = self._expect_identifier("context set name")
        self._expect_symbol("{")
        resources = []
        while not self._matches_symbol("}"):
            resources.append(self._parse_resource_ref("CONTEXT_SET"))
            self._expect_symbol(";")
        self._expect_symbol("}")
        self._consume_optional_semicolon()
        return ast_module.ContextSetDecl(name=name, resources=resources, location=start.location)

    def _parse_python(
        self,
        forced_id: str | None = None,
        end_on_slot: bool = False,
        end_on_parallel_step: bool = False,
    ) -> ast_module.PythonDecl:
        start = self._expect_keyword("PY") if forced_id is None else self._peek()
        node_id = forced_id or self._expect_identifier("python node id")
        script_path: str | None = None
        timeout_seconds: int | None = None
        timeout_unlimited = False
        instruction_path: ast_module.StateRef | None = None
        result_path: ast_module.StateRef | None = None
        updates_state = False

        while not self._should_end_task(end_on_slot, end_on_parallel_step):
            if self._matches_keyword("SCRIPT"):
                self._advance()
                script_path = self._expect_string("SCRIPT path")
            elif self._matches_keyword("TIMEOUT"):
                self._advance()
                timeout_seconds, timeout_unlimited = self._parse_timeout_value("TIMEOUT")
            elif self._matches_keyword("INSTRUCTION"):
                self._advance()
                instruction_path = self._expect_state_ref("INSTRUCTION")
            elif self._matches_keyword("RESULT"):
                self._advance()
                result_path = self._expect_state_ref("RESULT")
            elif self._matches_keyword("UPDATES_STATE"):
                self._advance()
                updates_state = True
            else:
                raise errors_module.DSLParseError(
                    f"Unexpected PY token: {self._peek().value}",
                    self._peek().location,
                )
        if not end_on_slot and not end_on_parallel_step:
            self._expect_symbol(";")
        if script_path is None:
            raise errors_module.DSLParseError("PY requires SCRIPT.", start.location)
        return ast_module.PythonDecl(
            id=node_id,
            script_path=script_path,
            timeout_seconds=timeout_seconds,
            timeout_unlimited=timeout_unlimited,
            instruction_path=instruction_path,
            result_path=result_path,
            updates_state=updates_state,
            location=start.location,
        )

    def _parse_tool(
        self,
        forced_id: str | None = None,
        end_on_slot: bool = False,
        end_on_parallel_step: bool = False,
    ) -> ast_module.ToolDecl:
        start = self._expect_keyword("TOOL") if forced_id is None else self._peek()
        node_id = forced_id or self._expect_identifier("tool node id")
        tool_name: str | None = None
        options: dict[str, object] = {}
        timeout_seconds: int | None = None
        timeout_unlimited = False
        result_path: ast_module.StateRef | None = None
        seen: set[str] = set()

        while not self._should_end_task(end_on_slot, end_on_parallel_step):
            field = self._peek().value.upper()
            if field not in {"USE", "OPTIONS", "TIMEOUT", "RESULT"}:
                raise errors_module.DSLParseError(
                    f"Unexpected TOOL token: {self._peek().value}",
                    self._peek().location,
                )
            if field in seen:
                raise errors_module.DSLParseError(
                    f"Duplicate TOOL field: {field}.",
                    self._peek().location,
                )
            seen.add(field)
            self._advance()
            if field == "USE":
                tool_name = self._expect_identifier("tool name")
            elif field == "OPTIONS":
                value = self._parse_json_value()
                if not isinstance(value, dict):
                    raise errors_module.DSLParseError(
                        "OPTIONS must be a JSON object.",
                        self._peek().location,
                    )
                options = value
            elif field == "TIMEOUT":
                timeout_seconds, timeout_unlimited = self._parse_timeout_value("TIMEOUT")
            else:
                result_path = self._expect_state_ref("RESULT")

        if not end_on_slot and not end_on_parallel_step:
            self._expect_symbol(";")
        if tool_name is None:
            raise errors_module.DSLParseError("TOOL requires USE.", start.location)
        return ast_module.ToolDecl(
            id=node_id,
            tool_name=tool_name,
            options=options,
            timeout_seconds=timeout_seconds,
            timeout_unlimited=timeout_unlimited,
            result_path=result_path,
            location=start.location,
        )

    def _parse_codex(
        self,
        forced_id: str | None = None,
        end_on_slot: bool = False,
        end_on_parallel_step: bool = False,
    ) -> ast_module.CodexDecl:
        start = self._expect_keyword("CODEX") if forced_id is None else self._peek()
        node_id = forced_id or self._expect_identifier("codex node id")
        prompt_path: str | None = None
        contexts: list[ast_module.ContextRef] = []
        target_dirs: list[str] = []
        target_files: list[str] = []
        target_dirs_path: ast_module.StateRef | None = None
        target_files_path: ast_module.StateRef | None = None
        output_json_path: str | None = None
        output_json_mode: str | None = None
        output_file_paths: list[str] = []
        timeout_seconds: int | None = None
        timeout_unlimited = False
        instruction_path: ast_module.StateRef | None = None
        result_path: ast_module.StateRef | None = None

        while not self._should_end_task(end_on_slot, end_on_parallel_step):
            if self._matches_keyword("PROMPT") or self._matches_keyword("PROMPT_REF"):
                self._advance()
                prompt_path = self._expect_string("PROMPT path")
            elif self._matches_keyword("CONTEXT"):
                self._advance()
                contexts.append(self._parse_context_ref())
            elif self._matches_keyword("TARGET_DIR"):
                self._advance()
                target_dirs.append(self._expect_string("TARGET_DIR path"))
            elif self._matches_keyword("TARGET_FILE"):
                self._advance()
                target_files.append(self._expect_string("TARGET_FILE path"))
            elif self._matches_keyword("TARGET_DIRS"):
                self._advance()
                target_dirs_path = self._expect_state_ref("TARGET_DIRS")
            elif self._matches_keyword("TARGET_FILES"):
                self._advance()
                target_files_path = self._expect_state_ref("TARGET_FILES")
            elif self._matches_keyword("OUTPUT_JSON"):
                self._advance()
                output_json_path = self._expect_string("OUTPUT_JSON path")
                if self._matches_keyword("AS_FILE"):
                    self._advance()
                    output_json_mode = "file"
            elif self._matches_keyword("OUTPUT_FILE"):
                self._advance()
                output_file_paths.append(self._expect_string("OUTPUT_FILE path"))
            elif self._matches_keyword("TIMEOUT"):
                self._advance()
                timeout_seconds, timeout_unlimited = self._parse_timeout_value("TIMEOUT")
            elif self._matches_keyword("INSTRUCTION"):
                self._advance()
                instruction_path = self._expect_state_ref("INSTRUCTION")
            elif self._matches_keyword("RESULT"):
                self._advance()
                result_path = self._expect_state_ref("RESULT")
            else:
                raise errors_module.DSLParseError(
                    f"Unexpected CODEX token: {self._peek().value}",
                    self._peek().location,
                )
        if not end_on_slot and not end_on_parallel_step:
            self._expect_symbol(";")
        if prompt_path is None:
            raise errors_module.DSLParseError("CODEX requires PROMPT.", start.location)
        return ast_module.CodexDecl(
            id=node_id,
            prompt_path=prompt_path,
            contexts=contexts,
            target_dirs=target_dirs,
            target_files=target_files,
            target_dirs_path=target_dirs_path,
            target_files_path=target_files_path,
            output_json_path=output_json_path,
            output_json_mode=output_json_mode,
            output_file_paths=output_file_paths,
            timeout_seconds=timeout_seconds,
            timeout_unlimited=timeout_unlimited,
            instruction_path=instruction_path,
            result_path=result_path,
            location=start.location,
        )

    def _parse_approval(self) -> ast_module.ApprovalDecl:
        start = self._expect_keyword("APPROVAL")
        node_id = self._expect_identifier("approval node id")
        prompt: str | None = None
        prompt_ref_path: str | None = None
        read_path: ast_module.StateRef | None = None
        write_path: ast_module.StateRef | None = None
        result_path: ast_module.StateRef | None = None
        persist_path: str | None = None
        route_on_decision = False
        timeout_seconds: int | None = None
        timeout_unlimited = False
        poll_interval_seconds: int | None = None

        while not self._matches_symbol(";"):
            if self._matches_keyword("PROMPT"):
                self._advance()
                prompt = self._expect_string("PROMPT text")
            elif self._matches_keyword("PROMPT_REF"):
                self._advance()
                prompt_ref_path = self._expect_string("PROMPT_REF path")
            elif self._matches_keyword("READ"):
                self._advance()
                read_path = self._expect_state_ref("READ")
            elif self._matches_keyword("WRITE"):
                self._advance()
                write_path = self._expect_state_ref("WRITE")
            elif self._matches_keyword("RESULT"):
                self._advance()
                result_path = self._expect_state_ref("RESULT")
            elif self._matches_keyword("PERSIST"):
                self._advance()
                persist_path = self._expect_string("PERSIST path")
            elif self._matches_keyword("ROUTE_ON_DECISION"):
                self._advance()
                route_on_decision = True
            elif self._matches_keyword("TIMEOUT"):
                self._advance()
                timeout_seconds, timeout_unlimited = self._parse_timeout_value("TIMEOUT")
            elif self._matches_keyword("POLL"):
                self._advance()
                poll_interval_seconds = self._expect_positive_int("POLL")
            else:
                raise errors_module.DSLParseError(
                    f"Unexpected APPROVAL token: {self._peek().value}",
                    self._peek().location,
                )
        self._expect_symbol(";")
        if (prompt is None) == (prompt_ref_path is None):
            raise errors_module.DSLParseError(
                "APPROVAL requires exactly one of PROMPT or PROMPT_REF.",
                start.location,
            )
        if read_path is None:
            raise errors_module.DSLParseError("APPROVAL requires READ state.*.", start.location)
        if write_path is None:
            raise errors_module.DSLParseError("APPROVAL requires WRITE state.*.", start.location)
        return ast_module.ApprovalDecl(
            id=node_id,
            prompt=prompt,
            prompt_ref_path=prompt_ref_path,
            read_path=read_path,
            write_path=write_path,
            result_path=result_path,
            persist_path=persist_path,
            route_on_decision=route_on_decision,
            timeout_seconds=timeout_seconds,
            timeout_unlimited=timeout_unlimited,
            poll_interval_seconds=poll_interval_seconds,
            location=start.location,
        )

    def _parse_react(
        self,
        forced_id: str | None = None,
        end_on_parallel_step: bool = False,
    ) -> ast_module.ReactDecl:
        start = self._expect_keyword("REACT") if forced_id is None else self._peek()
        node_id = forced_id or self._expect_identifier("react node id")
        if self._matches_keyword("MAX_STEPS"):
            raise errors_module.DSLParseError(
                "MAX_STEPS syntax is not supported in Authoring DSL v2. Use MAX.",
                self._peek().location,
            )
        self._expect_keyword("MAX")
        max_steps = self._expect_positive_int("MAX")
        slots: dict[str, ast_module.ReactSlotDecl] = {}
        spec_path: str | None = None
        on_max_ask: ast_module.ReactOnMaxAskDecl | None = None

        while not self._should_end_react(end_on_parallel_step):
            if self._matches_keyword("SPEC"):
                if spec_path is not None:
                    raise errors_module.DSLParseError(
                        "Duplicate REACT SPEC.",
                        self._peek().location,
                    )
                self._advance()
                spec_path = self._expect_string("SPEC path")
                continue
            if self._matches_keyword("ON_MAX"):
                if on_max_ask is not None:
                    raise errors_module.DSLParseError(
                        "Duplicate REACT ON_MAX ASK block.",
                        self._peek().location,
                    )
                on_max_ask = self._parse_react_on_max_ask()
                continue
            if not self._is_react_slot_keyword():
                raise errors_module.DSLParseError(
                    f"Unexpected REACT token: {self._peek().value}",
                    self._peek().location,
                )
            slot_token = self._advance()
            slot_name = slot_token.value.lower()
            if slot_name in slots:
                raise errors_module.DSLParseError(
                    f"Duplicate REACT slot: {slot_name}.",
                    slot_token.location,
                )
            task_id = f"{node_id}__{slot_name}"
            if self._matches_keyword("WORKFLOW"):
                self._advance()
                workflow_task_id = self._expect_identifier(f"REACT {slot_name} WORKFLOW id")
                task = self._parse_slot_workflow_ref(
                    workflow_task_id,
                    f"REACT {slot_name} WORKFLOW",
                    end_on_slot=True,
                    end_on_parallel_step=end_on_parallel_step,
                )
            elif self._matches_keyword("TOOL"):
                self._advance()
                task = self._parse_tool(
                    forced_id=task_id,
                    end_on_slot=True,
                    end_on_parallel_step=end_on_parallel_step,
                )
            elif slot_name == "decide":
                self._expect_keyword("PY")
                task = self._parse_python(
                    forced_id=task_id,
                    end_on_slot=True,
                    end_on_parallel_step=end_on_parallel_step,
                )
            else:
                self._expect_keyword("CODEX")
                task = self._parse_codex(
                    forced_id=task_id,
                    end_on_slot=True,
                    end_on_parallel_step=end_on_parallel_step,
                )
            slots[slot_name] = ast_module.ReactSlotDecl(slot_name=slot_name, task=task, location=slot_token.location)

        if not end_on_parallel_step:
            self._expect_symbol(";")
        for slot_name in self.REACT_SLOTS:
            if slot_name not in slots:
                raise errors_module.DSLParseError(f"REACT missing slot: {slot_name}.", start.location)
        return ast_module.ReactDecl(
            id=node_id,
            max_steps=max_steps,
            slots=slots,
            spec_path=spec_path,
            on_max_ask=on_max_ask,
            location=start.location,
        )

    def _parse_agent_loop(self) -> ast_module.AgentLoopDecl:
        start = self._expect_keyword("AGENT_LOOP")
        node_id = self._expect_identifier("agent loop node id")
        max_iterations: int | None = None
        artifacts_path: str | None = None
        status_path: ast_module.StateRef | None = None
        report_path: ast_module.StateRef | None = None
        on_max = "block"
        on_error = "block"
        token_max = 1000000
        seen_header: set[str] = set()

        while not self._matches_symbol("{"):
            field = self._peek().value.upper()
            if field not in {"MAX_ITERATIONS", "ARTIFACTS", "STATUS", "REPORT", "TOKEN_MAX", "ON_MAX", "ON_ERROR"}:
                raise errors_module.DSLParseError(
                    f"Unexpected AGENT_LOOP header token: {self._peek().value}",
                    self._peek().location,
                )
            if field in seen_header:
                raise errors_module.DSLParseError(f"Duplicate AGENT_LOOP header field: {field}.", self._peek().location)
            seen_header.add(field)
            self._advance()
            if field == "MAX_ITERATIONS":
                max_iterations = self._expect_positive_int("MAX_ITERATIONS")
            elif field == "ARTIFACTS":
                artifacts_path = self._expect_string("ARTIFACTS path")
            elif field == "STATUS":
                status_path = self._expect_state_ref("STATUS")
            elif field == "REPORT":
                report_path = self._expect_state_ref("REPORT")
            elif field == "TOKEN_MAX":
                token_max = self._expect_positive_int("TOKEN_MAX")
            elif field == "ON_MAX":
                on_max = self._expect_agent_loop_policy("ON_MAX")
            else:
                on_error = self._expect_agent_loop_policy("ON_ERROR")

        self._expect_symbol("{")
        goal: str | None = None
        contexts: list[ast_module.ContextRef] = []
        slots: dict[str, ast_module.AgentLoopSlotDecl] = {}
        slot_order: list[str] = []

        while not self._matches_symbol("}"):
            if self._matches_keyword("GOAL"):
                if goal is not None:
                    raise errors_module.DSLParseError("Duplicate AGENT_LOOP GOAL.", self._peek().location)
                self._advance()
                goal = self._expect_string("GOAL")
                self._consume_optional_semicolon()
                continue
            if self._matches_keyword("CONTEXT"):
                self._advance()
                contexts.append(self._parse_context_ref())
                self._consume_optional_semicolon()
                continue
            if not self._is_agent_loop_slot_keyword():
                raise errors_module.DSLParseError(
                    f"Unexpected AGENT_LOOP token: {self._peek().value}",
                    self._peek().location,
                )
            slot_token = self._advance()
            slot_name = slot_token.value.lower()
            if slot_name in slots:
                raise errors_module.DSLParseError(f"Duplicate AGENT_LOOP slot: {slot_name}.", slot_token.location)
            task = self._parse_agent_loop_slot_task(slot_name)
            self._validate_agent_loop_slot_task(slot_name, task, slot_token.location)
            slots[slot_name] = ast_module.AgentLoopSlotDecl(slot_name=slot_name, task=task, location=slot_token.location)
            slot_order.append(slot_name)

        self._expect_symbol("}")
        self._consume_optional_semicolon()

        if max_iterations is None:
            raise errors_module.DSLParseError("AGENT_LOOP requires MAX_ITERATIONS.", start.location)
        if artifacts_path is None:
            raise errors_module.DSLParseError("AGENT_LOOP requires ARTIFACTS.", start.location)
        if goal is None:
            raise errors_module.DSLParseError("AGENT_LOOP requires GOAL.", start.location)
        for slot_name in self.AGENT_LOOP_SLOTS:
            if slot_name not in slots:
                raise errors_module.DSLParseError(f"AGENT_LOOP missing slot: {slot_name}.", start.location)

        return ast_module.AgentLoopDecl(
            id=node_id,
            max_iterations=max_iterations,
            artifacts_path=artifacts_path,
            goal=goal,
            contexts=contexts,
            slots=slots,
            slot_order=slot_order,
            on_max=on_max,
            on_error=on_error,
            token_max=token_max,
            status_path=status_path,
            report_path=report_path,
            location=start.location,
        )

    def _expect_agent_loop_policy(self, label: str) -> str:
        token = self._peek()
        policy = self._expect_identifier(label).lower()
        if policy not in {"block", "wait_human"}:
            raise errors_module.DSLParseError(
                f"{label} must be block or wait_human.",
                token.location,
            )
        return policy

    def _parse_agent_loop_slot_task(
        self,
        slot_name: str,
    ) -> ast_module.PythonDecl | ast_module.ToolDecl | ast_module.CodexDecl | ast_module.WorkflowRefDecl:
        if self._matches_keyword("CODEX"):
            self._advance()
            task_id = self._expect_identifier(f"AGENT_LOOP {slot_name} CODEX id")
            return self._parse_codex(forced_id=task_id)
        if self._matches_keyword("PY"):
            self._advance()
            task_id = self._expect_identifier(f"AGENT_LOOP {slot_name} PY id")
            return self._parse_python(forced_id=task_id)
        if self._matches_keyword("TOOL"):
            self._advance()
            task_id = self._expect_identifier(f"AGENT_LOOP {slot_name} TOOL id")
            return self._parse_tool(forced_id=task_id)
        if self._matches_keyword("WORKFLOW"):
            self._advance()
            task_id = self._expect_identifier(f"AGENT_LOOP {slot_name} WORKFLOW id")
            return self._parse_slot_workflow_ref(task_id, f"AGENT_LOOP {slot_name} WORKFLOW")
        raise errors_module.DSLParseError(
            f"AGENT_LOOP slot {slot_name} requires CODEX, PY, TOOL, or WORKFLOW.",
            self._peek().location,
        )

    def _parse_slot_workflow_ref(
        self,
        task_id: str,
        label: str,
        *,
        end_on_slot: bool = False,
        end_on_parallel_step: bool = False,
    ) -> ast_module.WorkflowRefDecl:
        start = self._peek()
        workflow_path: str | None = None
        result_path: ast_module.StateRef | None = None
        seen: set[str] = set()
        while not self._should_end_task(end_on_slot, end_on_parallel_step=end_on_parallel_step):
            field = self._peek().value.upper()
            if field not in {"WORKFLOW", "RESULT"}:
                raise errors_module.DSLParseError(
                    f"Unexpected {label} token: {self._peek().value}",
                    self._peek().location,
                )
            if field in seen:
                raise errors_module.DSLParseError(
                    f"Duplicate {label} field: {field}.",
                    self._peek().location,
                )
            seen.add(field)
            self._advance()
            if field == "WORKFLOW":
                workflow_path = self._expect_string(f"{label} path")
            else:
                result_path = self._expect_state_ref(f"{label} RESULT")
        if not end_on_slot and not end_on_parallel_step:
            self._expect_symbol(";")
        if workflow_path is None:
            raise errors_module.DSLParseError(f"{label} requires WORKFLOW path.", start.location)
        if result_path is None:
            raise errors_module.DSLParseError(f"{label} requires RESULT state.*.", start.location)
        return ast_module.WorkflowRefDecl(
            id=task_id,
            workflow_path=workflow_path,
            result_path=result_path,
            location=start.location,
        )

    def _validate_agent_loop_slot_task(
        self,
        slot_name: str,
        task: ast_module.PythonDecl | ast_module.ToolDecl | ast_module.CodexDecl | ast_module.WorkflowRefDecl,
        location,
    ) -> None:
        if isinstance(task, ast_module.CodexDecl) and (
            task.target_dirs
            or task.target_files
            or task.target_dirs_path is not None
            or task.target_files_path is not None
        ):
            raise errors_module.DSLParseError(
                "AGENT_LOOP CODEX slots cannot declare TARGET_DIRS or TARGET_FILES.",
                location,
            )
        if slot_name in {"verify", "decide"} and not isinstance(
            task,
            (ast_module.PythonDecl, ast_module.WorkflowRefDecl),
        ):
            raise errors_module.DSLParseError(
                f"AGENT_LOOP slot {slot_name} must use PY or WORKFLOW.",
                location,
            )

    def _parse_parallel(self) -> ast_module.ParallelDecl:
        start = self._expect_keyword("PARALLEL")
        node_id = self._expect_identifier("parallel node id")
        max_concurrency: int | None = None
        fail_strategy: str | None = None
        if self._matches_keyword("MAX"):
            self._advance()
            max_concurrency = self._expect_positive_int("MAX")
        if self._matches_keyword("FAIL"):
            self._advance()
            fail_strategy = self._expect_identifier("FAIL strategy")
            if fail_strategy not in {"fail_fast", "collect"}:
                raise errors_module.DSLParseError(
                    "FAIL strategy must be fail_fast or collect.",
                    self._peek().location,
                )

        steps: list[ast_module.ParallelStepDecl] = []
        while not self._matches_symbol(";"):
            steps.append(self._parse_parallel_step())
        self._expect_symbol(";")
        if not steps:
            raise errors_module.DSLParseError("PARALLEL requires at least one STEP.", start.location)
        return ast_module.ParallelDecl(
            id=node_id,
            steps=steps,
            max_concurrency=max_concurrency,
            fail_strategy=fail_strategy,
            location=start.location,
        )

    def _parse_parallel_step(self) -> ast_module.ParallelStepDecl:
        start = self._expect_keyword("STEP")
        step_id = self._expect_identifier("parallel step id")
        self._expect_keyword("OUTPUT")
        output_path = self._expect_state_ref("OUTPUT")
        self._expect_keyword("RESULT")
        result_path = self._expect_state_ref("RESULT")

        if self._matches_keyword("PY"):
            self._advance()
            task = self._parse_python(forced_id=step_id, end_on_parallel_step=True)
        elif self._matches_keyword("TOOL"):
            self._advance()
            task = self._parse_tool(forced_id=step_id, end_on_parallel_step=True)
        elif self._matches_keyword("CODEX"):
            self._advance()
            task = self._parse_codex(forced_id=step_id, end_on_parallel_step=True)
        elif self._matches_keyword("REACT"):
            self._advance()
            task = self._parse_react(forced_id=step_id, end_on_parallel_step=True)
        elif self._matches_keyword("WORKFLOW"):
            self._advance()
            workflow_path = self._expect_string("WORKFLOW path")
            task = ast_module.WorkflowRefDecl(
                id=step_id,
                workflow_path=workflow_path,
                location=start.location,
            )
        else:
            raise errors_module.DSLParseError(
                f"Unexpected PARALLEL STEP token: {self._peek().value}",
                self._peek().location,
            )
        return ast_module.ParallelStepDecl(
            id=step_id,
            output_path=output_path,
            result_path=result_path,
            task=task,
            location=start.location,
        )

    def _parse_react_on_max_ask(self) -> ast_module.ReactOnMaxAskDecl:
        start = self._expect_keyword("ON_MAX")
        self._expect_keyword("ASK")
        prompt: str | None = None
        read_path: ast_module.StateRef | None = None
        write_path: ast_module.StateRef | None = None
        result_path: ast_module.StateRef | None = None
        status_path: ast_module.StateRef | None = None
        extra_max_steps: int | None = None
        timeout_seconds: int | None = None
        timeout_unlimited = False
        poll_interval_seconds: int | None = None

        while not self._matches_symbol(";"):
            if self._is_react_slot_keyword():
                raise errors_module.DSLParseError(
                    f"Unexpected REACT slot after ON_MAX ASK: {self._peek().value}",
                    self._peek().location,
                )
            if self._matches_keyword("PROMPT"):
                self._advance()
                prompt = self._expect_string("PROMPT")
            elif self._matches_keyword("READ"):
                self._advance()
                read_path = self._expect_state_ref("READ")
            elif self._matches_keyword("WRITE"):
                self._advance()
                write_path = self._expect_state_ref("WRITE")
            elif self._matches_keyword("RESULT"):
                self._advance()
                result_path = self._expect_state_ref("RESULT")
            elif self._matches_keyword("STATUS"):
                self._advance()
                status_path = self._expect_state_ref("STATUS")
            elif self._matches_keyword("EXTRA_MAX"):
                self._advance()
                extra_max_steps = self._expect_positive_int("EXTRA_MAX")
            elif self._matches_keyword("TIMEOUT"):
                self._advance()
                timeout_seconds, timeout_unlimited = self._parse_timeout_value("TIMEOUT")
            elif self._matches_keyword("POLL"):
                self._advance()
                poll_interval_seconds = self._expect_positive_int("POLL")
            else:
                raise errors_module.DSLParseError(
                    f"Unexpected ON_MAX ASK token: {self._peek().value}",
                    self._peek().location,
                )

        if prompt is None:
            raise errors_module.DSLParseError("ON_MAX ASK requires PROMPT.", start.location)
        if read_path is None:
            raise errors_module.DSLParseError("ON_MAX ASK requires READ state.*.", start.location)
        if write_path is None:
            raise errors_module.DSLParseError("ON_MAX ASK requires WRITE state.*.", start.location)
        if extra_max_steps is None:
            raise errors_module.DSLParseError("ON_MAX ASK requires EXTRA_MAX.", start.location)
        return ast_module.ReactOnMaxAskDecl(
            prompt=prompt,
            read_path=read_path,
            write_path=write_path,
            result_path=result_path,
            status_path=status_path,
            extra_max_steps=extra_max_steps,
            timeout_seconds=timeout_seconds,
            timeout_unlimited=timeout_unlimited,
            poll_interval_seconds=poll_interval_seconds,
            location=start.location,
        )

    def _parse_edge(self) -> ast_module.EdgeDecl:
        start = self._expect_keyword("EDGE")
        from_node = self._expect_identifier("edge source")
        self._expect_keyword("TO")
        to_node = self._expect_identifier("edge target")
        self._expect_symbol(";")
        return ast_module.EdgeDecl(from_node, to_node, start.location)

    def _parse_flow(self) -> ast_module.FlowDecl | list[ast_module.FlowDecl | ast_module.RouteDecl]:
        start = self._expect_keyword("FLOW")
        if self._matches_symbol("{"):
            return self._parse_flow_block(start)
        nodes = [self._expect_identifier("flow node")]
        while self._matches_keyword("THEN"):
            self._advance()
            nodes.append(self._expect_identifier("flow node"))
        self._expect_symbol(";")
        if len(nodes) < 2:
            raise errors_module.DSLParseError("FLOW must include at least two nodes.", start.location)
        return ast_module.FlowDecl(nodes, start.location)

    def _parse_flow_block(self, start: tokens_module.Token) -> list[ast_module.FlowDecl | ast_module.RouteDecl]:
        self._expect_symbol("{")
        statements: list[ast_module.FlowDecl | ast_module.RouteDecl] = []
        while not self._matches_symbol("}"):
            item_start = self._peek()
            from_node = self._expect_identifier("flow block node")
            if self._matches_keyword("WHEN"):
                branches: dict[str, str] = {}
                while self._matches_keyword("WHEN"):
                    self._advance()
                    route_key = self._expect_string("route key")
                    self._expect_keyword("THEN")
                    branches[route_key] = self._expect_identifier("route target")
                self._expect_symbol(";")
                statements.append(ast_module.RouteDecl(from_node, branches, item_start.location))
            elif self._matches_keyword("THEN"):
                nodes = [from_node]
                while self._matches_keyword("THEN"):
                    self._advance()
                    nodes.append(self._expect_identifier("flow node"))
                self._expect_symbol(";")
                statements.append(ast_module.FlowDecl(nodes, item_start.location))
            else:
                raise errors_module.DSLParseError(
                    "FLOW block item must include THEN or WHEN.",
                    item_start.location,
                )
        self._expect_symbol("}")
        self._consume_optional_semicolon()
        if not statements:
            raise errors_module.DSLParseError("FLOW block must include at least one item.", start.location)
        return statements

    def _parse_route(self) -> ast_module.RouteDecl:
        start = self._expect_keyword("ROUTE")
        from_node = self._expect_identifier("route source")
        branches: dict[str, str] = {}
        while self._matches_keyword("WHEN"):
            self._advance()
            route_key = self._expect_string("route key")
            self._expect_keyword("THEN")
            branches[route_key] = self._expect_identifier("route target")
        self._expect_symbol(";")
        if not branches:
            raise errors_module.DSLParseError("ROUTE must include at least one WHEN branch.", start.location)
        return ast_module.RouteDecl(from_node, branches, start.location)

    def _parse_json_value(self) -> object:
        token = self._peek()
        if token.kind == tokens_module.TokenKind.STRING:
            return self._advance().value
        if self._matches_symbol("{"):
            self._advance()
            result: dict[str, object] = {}
            if self._matches_symbol("}"):
                self._advance()
                return result
            while True:
                key = self._expect_string("JSON object key")
                if key in result:
                    raise errors_module.DSLParseError(
                        f"Duplicate JSON object key: {key}.",
                        token.location,
                    )
                self._expect_symbol(":")
                result[key] = self._parse_json_value()
                if self._matches_symbol("}"):
                    self._advance()
                    return result
                self._expect_symbol(",")
        if self._matches_symbol("["):
            self._advance()
            result_list: list[object] = []
            if self._matches_symbol("]"):
                self._advance()
                return result_list
            while True:
                result_list.append(self._parse_json_value())
                if self._matches_symbol("]"):
                    self._advance()
                    return result_list
                self._expect_symbol(",")
        if token.kind == tokens_module.TokenKind.IDENT:
            raw = token.value
            if raw == "true":
                self._advance()
                return True
            if raw == "false":
                self._advance()
                return False
            if raw == "null":
                self._advance()
                return None
            try:
                value = json.loads(raw)
            except (ValueError, TypeError):
                pass
            else:
                if isinstance(value, int) and not isinstance(value, bool):
                    self._advance()
                    return value
                if isinstance(value, float) and math.isfinite(value):
                    self._advance()
                    return value
        raise errors_module.DSLParseError("Expected a valid JSON value.", token.location)

    def _parse_context_ref(self) -> ast_module.ContextRef:
        token = self._peek()
        if token.value.startswith("state."):
            raise errors_module.DSLParseError("CONTEXT cannot use state.*. Use READ state.* for runtime state.", token.location)
        if self._matches_keyword("workspace") or self._matches_keyword("workflow") or self._matches_keyword("file") or self._matches_keyword("dir"):
            resource = self._parse_resource_ref("CONTEXT")
            return ast_module.ContextRef(resource=resource, location=resource.location)
        context_set = self._expect_identifier("context set name")
        return ast_module.ContextRef(context_set=context_set, location=token.location)

    def _parse_resource_ref(self, context: str) -> ast_module.ResourceRef:
        token = self._peek()
        root = "workspace"
        if self._matches_keyword("workspace") or self._matches_keyword("workflow"):
            root = self._advance().value.lower()
        if not (self._matches_keyword("file") or self._matches_keyword("dir")):
            raise errors_module.DSLParseError(f"{context} resource must be file or dir.", token.location)
        ref_type = self._advance().value.lower()
        path = self._expect_string(f"{context} {ref_type} path")
        return ast_module.ResourceRef(type=ref_type, path=path, root=root, location=token.location)

    def _should_end_task(self, end_on_slot: bool, end_on_parallel_step: bool = False) -> bool:
        if self._matches_symbol(";"):
            return True
        if end_on_parallel_step and self._matches_keyword("STEP"):
            return True
        return end_on_slot and (
            self._is_react_slot_keyword()
            or self._matches_keyword("ON_MAX")
            or (end_on_parallel_step and self._matches_keyword("STEP"))
        )

    def _should_end_react(self, end_on_parallel_step: bool) -> bool:
        if self._matches_symbol(";"):
            return True
        return end_on_parallel_step and self._matches_keyword("STEP")

    def _expect_state_ref(self, label: str) -> ast_module.StateRef:
        token = self._peek()
        raw = self._expect_identifier(f"{label} state path")
        if not raw.startswith("state.") or len(raw) <= len("state."):
            raise errors_module.DSLParseError(f"{label} must use a state.* path.", token.location)
        return ast_module.StateRef(raw[len("state."):], token.location)

    def _expect_keyword(self, keyword: str) -> tokens_module.Token:
        token = self._peek()
        if not self._matches_keyword(keyword):
            raise errors_module.DSLParseError(f"Expected {keyword}.", token.location)
        return self._advance()

    def _expect_identifier(self, label: str) -> str:
        token = self._peek()
        if token.kind != tokens_module.TokenKind.IDENT:
            raise errors_module.DSLParseError(f"Expected {label}.", token.location)
        return self._advance().value

    def _expect_string(self, label: str) -> str:
        token = self._peek()
        if token.kind != tokens_module.TokenKind.STRING:
            raise errors_module.DSLParseError(f"Expected {label} string.", token.location)
        return self._advance().value

    def _parse_timeout_value(self, label: str) -> tuple[int | None, bool]:
        if self._matches_keyword("none"):
            self._advance()
            return None, True
        return self._expect_positive_int(label), False

    def _expect_positive_int(self, label: str) -> int:
        token = self._peek()
        if token.kind != tokens_module.TokenKind.IDENT or not token.value.isdigit():
            raise errors_module.DSLParseError(f"{label} must be a positive integer.", token.location)
        value = int(self._advance().value)
        if value < 1:
            raise errors_module.DSLParseError(f"{label} must be a positive integer.", token.location)
        return value

    def _expect_symbol(self, symbol: str) -> None:
        token = self._peek()
        if token.kind != tokens_module.TokenKind.SYMBOL or token.value != symbol:
            raise errors_module.DSLParseError(f"Expected '{symbol}'.", token.location)
        self._advance()

    def _consume_optional_semicolon(self) -> None:
        if self._matches_symbol(";"):
            self._advance()

    def _matches_keyword(self, keyword: str) -> bool:
        token = self._peek()
        return token.kind == tokens_module.TokenKind.IDENT and token.value.upper() == keyword.upper()

    def _matches_symbol(self, symbol: str) -> bool:
        token = self._peek()
        return token.kind == tokens_module.TokenKind.SYMBOL and token.value == symbol

    def _is_react_slot_keyword(self) -> bool:
        token = self._peek()
        return token.kind == tokens_module.TokenKind.IDENT and token.value.lower() in self.REACT_SLOTS

    def _is_agent_loop_slot_keyword(self) -> bool:
        token = self._peek()
        return token.kind == tokens_module.TokenKind.IDENT and token.value.lower() in self.AGENT_LOOP_SLOTS

    def _peek(self) -> tokens_module.Token:
        return self.tokens[self.index]

    def _advance(self) -> tokens_module.Token:
        token = self.tokens[self.index]
        self.index += 1
        return token

    def _is_eof(self) -> bool:
        return self._peek().kind == tokens_module.TokenKind.EOF
