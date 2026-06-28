# LGWF Codex Handoff

You are running inside the client workspace.

Workspace root:
{{workspace_root}}

Main prompt file:
{{main_prompt_path}}

Governing spec file:
{{spec_path}}

Reference context:
{{context_paths}}

Analysis target directories:
{{target_dirs}}

Analysis target files:
{{target_files}}

Instructions:
1. If a governing spec file is provided, read it first.
2. Read the main prompt file.
3. The governing spec is authoritative. If it conflicts with the main prompt, follow the governing spec.
4. Read every listed reference file or directory that is relevant to the task.
5. Treat paths in the main prompt as relative to the workspace root unless the prompt says otherwise.
6. Follow the main prompt after applying the governing spec.
7. Do not invent facts that are not supported by the spec, prompt, or reference files.
8. Only analyze files under Analysis targets. Do not treat Reference context as analysis targets.

