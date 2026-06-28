import pathlib
from typing import Any

import lgwf_dsl.artifact_contracts as artifact_contracts_module
import lgwf_dsl.compiler as compiler_module
import lgwf_dsl.diagnostics as diagnostics_module
import lgwf_dsl.errors as errors_module
import lgwf_dsl.explainer as explainer_module
import lgwf_dsl.linter as linter_module
import lgwf_dsl.parser as parser_module
import lgwf_dsl.runtime_debug as runtime_debug_module
import lgwf_dsl.validator as validator_module


class WorkflowAuditor:
    def audit(
        self,
        input_path: pathlib.Path,
        *,
        debug_runtime: bool = False,
        bundled_wheel: str | pathlib.Path | None = None,
    ) -> tuple[dict[str, Any], int]:
        payload: dict[str, Any] = {
            "passed": False,
            "summary": "Workflow authoring audit did not complete.",
            "input": str(input_path),
            "workflow": {},
            "diagnostics": [],
            "explain": None,
        }
        if debug_runtime:
            payload["runtime_debug"] = runtime_debug_module.collect_runtime_debug(
                bundled_wheel=bundled_wheel,
            )

        try:
            source = input_path.read_text(encoding="utf-8")
            ast = parser_module.Parser.from_text(source, source_name=str(input_path)).parse_workflow()
            payload["workflow"] = {
                "name": ast.name,
                "entry_point": ast.entry_point,
            }
            validator_module.WorkflowValidator().validate(ast)
        except errors_module.DSLError as exc:
            payload["diagnostics"] = [
                self._diagnostic(
                    exc.message,
                    exc.location,
                    code=exc.code,
                    suggestion=exc.suggestion or "Fix the reported workflow.lgwf syntax or semantic error, then rerun audit.",
                ).to_dict()
            ]
            payload["summary"] = "Workflow authoring audit failed before lint."
            return payload, 1

        diagnostics = linter_module.WorkflowLinter(package_root=input_path.parent).lint(ast)
        diagnostics.extend(artifact_contracts_module.ArtifactContractAuditor(input_path.parent).audit(ast))
        try:
            workflow = compiler_module.WorkflowDslCompiler().compile_text(
                source,
                source_name=str(input_path),
                package_root=input_path.parent,
            )
            payload["explain"] = explainer_module.WorkflowExplainer().explain(workflow)
        except Exception as exc:
            diagnostics.append(
                self._diagnostic(
                    f"{type(exc).__name__}: {exc}",
                    None,
                    code="LGWF_COMPILE_ERROR",
                    suggestion="Fix the compile/lowering error, then rerun audit.",
                )
            )

        payload["diagnostics"] = [diagnostic.to_dict() for diagnostic in diagnostics]
        payload["passed"] = not any(diagnostic.severity in {"error", "warning"} for diagnostic in diagnostics)
        if payload["passed"]:
            payload["summary"] = "Workflow authoring audit passed."
            return payload, 0
        payload["summary"] = f"Workflow authoring audit found {len(diagnostics)} issue(s)."
        return payload, 1

    def _diagnostic(
        self,
        message: str,
        location: diagnostics_module.SourceLocation | None,
        *,
        code: str,
        suggestion: str,
    ) -> diagnostics_module.Diagnostic:
        return diagnostics_module.Diagnostic(
            message,
            location,
            severity="error",
            code=code,
            suggestion=suggestion,
        )
