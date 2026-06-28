import argparse
import json
import pathlib
import sys
from typing import TextIO

import lgwf_dsl.artifact_contracts as artifact_contracts_module
import lgwf_dsl.auditor as auditor_module
import lgwf_dsl.compiler as compiler_module
import lgwf_dsl.explainer as explainer_module
import lgwf_dsl.linter as linter_module
import lgwf_dsl.parser as parser_module
import lgwf_dsl.runtime_debug as runtime_debug_module
import lgwf_dsl.validator as validator_module
import lgwf.compiler.dsl_schema as dsl_schema_module


def main(
    argv: list[str] | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    output = stdout or sys.stdout
    error_output = stderr or sys.stderr
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "compile":
            _compile_command(args, output, error_output)
            return 0
        if args.command == "explain":
            _explain_command(args, output)
            return 0
        if args.command == "lint":
            return _lint_command(args, output)
        if args.command == "audit":
            return _audit_command(args, output)
        if args.command == "debug-runtime":
            _debug_runtime_command(args, output)
            return 0
        if args.command == "schema":
            _schema_command(output)
            return 0
        raise ValueError(f"Unknown command: {args.command}")
    except Exception as exc:
        error_output.write(f"{type(exc).__name__}: {exc}\n")
        return 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m lgwf_dsl.cli",
        description="Compile LGWF SQL-like text DSL into workflow JSON.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    compile_parser = subparsers.add_parser(
        "compile",
        help="Compile a .lgwf workflow source file to workflow JSON.",
    )
    compile_parser.add_argument("input")
    compile_parser.add_argument("-o", "--output")

    explain_parser = subparsers.add_parser(
        "explain",
        help="Print a summary of a .lgwf workflow after lowering to workflow JSON.",
    )
    explain_parser.add_argument("input")

    lint_parser = subparsers.add_parser(
        "lint",
        help="Check a .lgwf workflow source file for risky authoring patterns.",
    )
    lint_parser.add_argument("input")

    audit_parser = subparsers.add_parser(
        "audit",
        help="Run an authoring-time audit and print machine-readable JSON diagnostics.",
    )
    audit_parser.add_argument("input")
    audit_parser.add_argument("--debug-runtime", action="store_true")
    audit_parser.add_argument("--bundled-wheel", help=argparse.SUPPRESS)

    debug_parser = subparsers.add_parser(
        "debug-runtime",
        help="Print LGWF DSL runtime import paths and feature flags.",
    )
    debug_parser.add_argument("--bundled-wheel")

    subparsers.add_parser(
        "schema",
        help="Print the machine-readable workflow DSL schema JSON.",
    )
    return parser


def _compile_command(args: argparse.Namespace, stdout: TextIO, stderr: TextIO) -> None:
    input_path = _resolve_input(args.input)
    source = input_path.read_text(encoding="utf-8")
    workflow = compiler_module.WorkflowDslCompiler().compile_text(
        source,
        source_name=str(input_path),
        package_root=input_path.parent,
    )
    content = json.dumps(workflow, ensure_ascii=False, indent=2, sort_keys=True)

    if args.output:
        output_path = pathlib.Path(args.output).expanduser().resolve()
        output_path.write_text(f"{content}\n", encoding="utf-8")
        stderr.write(f"[lgwf_dsl] compiled input={input_path} output={output_path}\n")
    else:
        stdout.write(f"{content}\n")


def _explain_command(args: argparse.Namespace, stdout: TextIO) -> None:
    input_path = _resolve_input(args.input)
    source = input_path.read_text(encoding="utf-8")
    workflow = compiler_module.WorkflowDslCompiler().compile_text(
        source,
        source_name=str(input_path),
        package_root=input_path.parent,
    )
    summary = explainer_module.WorkflowExplainer().explain(workflow)
    content = json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True)
    stdout.write(f"{content}\n")


def _lint_command(args: argparse.Namespace, stdout: TextIO) -> int:
    input_path = _resolve_input(args.input)
    source = input_path.read_text(encoding="utf-8")
    ast = parser_module.Parser.from_text(source, source_name=str(input_path)).parse_workflow()
    validator_module.WorkflowValidator().validate(ast)
    diagnostics = linter_module.WorkflowLinter(package_root=input_path.parent).lint(ast)
    diagnostics.extend(artifact_contracts_module.ArtifactContractAuditor(input_path.parent).audit(ast))
    if not diagnostics:
        stdout.write("[lgwf_dsl] lint passed\n")
        return 0
    for diagnostic in diagnostics:
        stdout.write(f"{diagnostic.format()}\n")
    return 1


def _audit_command(args: argparse.Namespace, stdout: TextIO) -> int:
    input_path = _resolve_input(args.input)
    payload, exit_code = auditor_module.WorkflowAuditor().audit(
        input_path,
        debug_runtime=args.debug_runtime,
        bundled_wheel=args.bundled_wheel,
    )
    content = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    stdout.write(f"{content}\n")
    return exit_code


def _debug_runtime_command(args: argparse.Namespace, stdout: TextIO) -> None:
    payload = runtime_debug_module.collect_runtime_debug(bundled_wheel=args.bundled_wheel)
    content = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    stdout.write(f"{content}\n")


def _schema_command(stdout: TextIO) -> None:
    schema = dsl_schema_module.load_schema()
    content = json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True)
    stdout.write(f"{content}\n")


def _resolve_input(raw_path: str) -> pathlib.Path:
    path = pathlib.Path(raw_path).expanduser().resolve()
    if not path.is_file():
        raise ValueError(f"input must be an existing file: {raw_path}")
    return path


if __name__ == "__main__":
    raise SystemExit(main())
