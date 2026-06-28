import pathlib
from typing import Any

import lgwf.compiler.dsl as runtime_dsl_module
import lgwf_dsl.ast as ast_module
import lgwf_dsl.catalog as catalog_module
import lgwf_dsl.lowerer as lowerer_module
import lgwf_dsl.parser as parser_module
import lgwf_dsl.validator as validator_module


class WorkflowDslCompiler:
    def __init__(
        self,
        catalog: catalog_module.CapabilityCatalogView | None = None,
        validate_runtime_ir: bool = True,
    ) -> None:
        self.catalog = catalog or catalog_module.CapabilityCatalogView.load_default()
        self.validate_runtime_ir = validate_runtime_ir

    def parse_text(self, text: str, source_name: str | None = None) -> ast_module.WorkflowAst:
        return parser_module.Parser.from_text(text, source_name=source_name).parse_workflow()

    def compile_text(
        self,
        text: str,
        source_name: str | None = None,
        package_root: str | pathlib.Path | None = None,
    ) -> dict[str, Any]:
        ast = self.parse_text(text, source_name=source_name)
        validator_module.WorkflowValidator(self.catalog).validate(ast)
        workflow = lowerer_module.WorkflowLowerer().lower(ast, package_root=package_root)
        if self.validate_runtime_ir:
            runtime_dsl_module.validate_dsl(workflow)
        return workflow
