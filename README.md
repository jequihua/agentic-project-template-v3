# Artifact-First Project Template v3

This repository is a clean starting point for an artifact-first agentic software
project.

The core idea: progress is an artifact becoming more explicit, reviewable, or
correct. The scaffold starts with one current-state file, clear active
workspaces, proportional ceremony, and optional memory/tooling lanes.

## Start Here

1. Read `CLAUDE.md`.
2. Read `PROJECT_STATE.md`.
3. Read the role-specific prompt in `initialization/`.
4. Use only active workspaces listed in `PROJECT_STATE.md` unless a prompt
   activates more.
5. Keep changes narrow, documented, and reviewable.

Adopting this template in a new or existing repo? See
`docs/template_framework/migration_and_adoption.md`.

Human owner starting from scratch? See
`docs/template_framework/human_user_manual.md`.

## Optional Lanes

- `llloom` memory is optional. Default memory mode is `none`.
- `frutlups` loop tooling is optional. The template must work manually without
  it.
- The optional OKF/profile lane ships a versioned document-profile candidate
  (`0.1-rc.1`), a read-only `--profile` checker, a disposable navigation-view
  generator, and an opt-in authoring guide. It is off by default: legacy
  no-frontmatter Markdown stays the norm, and a project opts in per new artifact
  only if it wants profiled metadata. See
  `docs/template_framework/okf_authoring_and_migration.md`, with
  `docs/template_framework/architect_operating_card.md` as the routine architect
  quick start.
- Inactive workspaces are placeholders, not obligations.
- Workspace activation and profiles: see
  `docs/template_framework/project_profiles.md`. The default is the `base`
  profile; optional workspaces are activated explicitly, not automatically.

## Initial Status

The repository starts as a blank project scaffold. Run the framework
initialization and project intake prompts before assigning implementation work.
