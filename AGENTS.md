# AGENTS.md — Darktide-BD repository rules

This file contains repository-level instructions for any AI/coding agent taking over this project.

## Mandatory GitHub Actions quota policy

- **Do not add scheduled GitHub Actions to this repository.**
- Never add `schedule:`, `cron:`, or any equivalent time-based periodic trigger under `.github/workflows/`.
- The former daily schedule in `.github/workflows/refresh-trees.yml` (`15 3 * * *`) was deliberately removed on 2026-09-27 at the user's request. **Do not restore it.**
- Talent-tree refreshes must remain manual through `workflow_dispatch` or event-driven by explicit code changes.
- If recurring background automation is needed in the future, use a non-GitHub-Actions scheduler that does not consume GitHub Actions quota, and explain the change to the user before implementing it.
- Push-triggered Pages deployment, tests, and audits are allowed. The prohibition is specifically on time-based recurring GitHub Actions.
- Treat this as a persistent repository policy unless the user explicitly reverses it in a later instruction.

## Project handoff

Read `HANDOFF.md` before making structural UX, data-source, workflow, deployment, or automation changes. Preserve its non-regression rules unless the user explicitly asks to change them.
