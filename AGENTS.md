# AGENTS.md — Darktide-BD repository rules

This file contains repository-level instructions for any AI/coding agent taking over this project.

## Mandatory automation policy

- **Do not add scheduled GitHub Actions to this repository.**
- Never add `schedule:`, `cron:`, or any equivalent time-based periodic trigger under `.github/workflows/`.
- The former daily schedule in `.github/workflows/refresh-trees.yml` (`15 3 * * *`) was deliberately removed on 2026-09-27 at the user's request. **Do not restore it.**
- **Do not move automation to another platform.** This repository must not be configured to run automatically on Cloudflare, Supabase, Vercel, Netlify, external CI/CD services, server cron, hosted schedulers, webhook-driven runners, polling services, or similar third-party infrastructure.
- The ban on external automatic execution covers scheduled jobs, polling, push/webhook-triggered jobs, automatic refreshes, background workers, and automatic deployments that execute this repository on another platform.
- Talent-tree refreshes may use this repository's existing GitHub `workflow_dispatch` manual action or the existing GitHub event-driven workflow behavior, but do not create a new external automation path.
- Existing GitHub push-triggered Pages deployment, tests, and audits may remain. The special restriction above is that there must be no time-based GitHub Actions and no automatic execution of this repository on any other platform.
- If an external platform is ever needed, it must be manually invoked for a one-off task unless the user explicitly changes this policy first.
- Treat this as a persistent repository policy unless the user explicitly reverses it in a later instruction.

## Project handoff

Read `HANDOFF.md` before making structural UX, data-source, workflow, deployment, or automation changes. Preserve its non-regression rules unless the user explicitly asks to change them.
