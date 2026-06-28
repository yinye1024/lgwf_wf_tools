import lgwf.compiler.dsl as compiler_module
import lgwf.workflows.registry as workflow_registry_module


graph = compiler_module.compile_dsl(workflow_registry_module.load_workflow_dsl())

