# LGWF Codex Plugins

This repository contains Codex plugins shared by the team.

## Layout

- `.agents/plugins/marketplace.json` - team marketplace manifest.
- `plugins/team-skills/` - shared Codex skills plugin.
- `plugins/team-skills/skills/` - individual team skill folders.

## Install Locally

From this repository root, add the marketplace:

```powershell
codex plugin marketplace add D:\allen\github\lgwf_plugins
codex plugin add team-skills@lgwf-team
```

Start a new Codex thread after installing or updating the plugin so newly added skills are loaded.

## Add A Skill

Create each new skill under `plugins/team-skills/skills/<skill-name>/`. Use lowercase hyphen-case names and keep each `SKILL.md` focused on the procedures Codex must follow.

Validate before sharing changes:

```powershell
python C:\Users\Administrator\.codex\skills\.system\skill-creator\scripts\quick_validate.py plugins\team-skills\skills\team-workflow
python C:\Users\Administrator\.codex\skills\.system\plugin-creator\scripts\validate_plugin.py plugins\team-skills
```
