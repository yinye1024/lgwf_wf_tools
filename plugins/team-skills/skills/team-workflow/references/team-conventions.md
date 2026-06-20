# Team Conventions

Use this file for conventions that should be shared across team skills. Keep it concise and update it when the team agrees on a new default.

## Content Language Defaults

- When creating or rewriting human-facing text files, including Markdown docs, README, prompts, report templates, skill references, and approval templates, default the body text to Chinese unless the user explicitly requests another language.
- Keep code, JSON key, YAML key, DSL capability names, file paths, commands, API fields, error codes, and protocol identifiers in their original form.
- When editing an existing file, follow the language style already established in that file.

## Development Defaults

- Inspect the repository before changing code.
- Preserve unrelated user changes in the working tree.
- Prefer existing project patterns over introducing new abstractions.
- Keep changes scoped to the requested behavior.
- Run the narrowest meaningful verification first, then broaden tests when shared behavior changes.

## Delivery Checklist

- Summarize changed files and behavior.
- Report verification commands and their result.
- Call out any test or environment limitation.
- Avoid claiming completion until verification has run or the limitation is explicit.

## Adding Team Skills

- Add each skill under `plugins/team-skills/skills/<skill-name>/`.
- Use lowercase hyphen-case skill names.
- Keep `SKILL.md` focused on procedures Codex must follow.
- Move detailed policies, schemas, and examples into `references/` files.
- Validate the skill and plugin before handing it to users.
