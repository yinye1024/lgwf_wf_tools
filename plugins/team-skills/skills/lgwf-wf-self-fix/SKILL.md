---
name: lgwf-wf-self-fix
description: Run an LGWF workflow through a self-repair loop. Use when the user wants to provide a target workflow.lgwf, collect that workflow's startup input once, run it, inspect LGWF logs/artifacts, directly fix the target workflow source, rerun until success, and proxy any human approvals in the current Codex conversation.
---

# LGWF Workflow Self Fix

Use this skill as the Codex-facing entrypoint for `lgwf_wf_self_fix`. The skill itself is a wrapper; the repair logic lives in `wf/workflow.lgwf`.

## Start

Always run through the LGWF facade:

```powershell
python C:\Users\Administrator\.codex\skills\lgwf-client-assist\scripts\lgwf.py run --workflow-lgwf plugins\team-skills\skills\lgwf-wf-self-fix\wf\workflow.lgwf --work-dir plugins\team-skills\skills\lgwf-wf-self-fix\ws --input-json "{}" --background
```

The workflow asks for `target_workflow_lgwf` and `max_attempts` in its first approval step. Do not pass those fields through startup `input-json`; the confirmed value is persisted to `.lgwf/self_fix_request_input.json`.

The fixed work dir is `plugins/team-skills/skills/lgwf-wf-self-fix/ws`. If it already contains prior LGWF data, follow the normal `lgwf-client-assist` continue/rerun flow instead of starting a second run blindly.

## Interaction Contract

The workflow collects inputs in two layers:

1. The workflow first asks the user to confirm the self-fix task: which `workflow.lgwf` to repair and the max retry count. It persists this to `.lgwf/self_fix_request_input.json`.
2. The workflow then analyzes the target workflow, asks the user for the target workflow's business startup JSON, and persists it to `.lgwf/target_workflow_input.json`.

After `.lgwf/target_workflow_input.json` is saved, every target workflow attempt must reuse that JSON object as the target workflow's `--input-json`.

## Runtime Handling

- Keep tracking the same `lgwf_wf_self_fix` run with `lgwf.py status` and `lgwf.py wait`.
- When `lgwf_wf_self_fix` asks for target startup parameters, show the generated contract and ask the user for a JSON object.
- When the target workflow enters `APPROVAL`, the self-fix workflow proxies that request. Ask the user to approve or reject in the current conversation, then continue the same run.
- Do not auto-approve target workflow approval requests.
- Do not create backups before repair; the target workflow source may be edited directly.

## Outputs

Inspect these artifacts under the fixed work dir:

- `.lgwf/self_fix_request.json`
- `.lgwf/self_fix_target.json`
- `.lgwf/target_input_contract.json`
- `.lgwf/target_workflow_input.json`
- `.lgwf/target_runs/attempt-*/`
- `.lgwf/target_failure_review.json`
- `.lgwf/self_fix_history.json`
- `reports/lgwf-wf-self-fix/final_report.md`
