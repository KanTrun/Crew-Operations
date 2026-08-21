# Repo Rename: CA-C-NG-B-NG → CA-CONG-BANG

**Date**: 2026-08-21 23:42  
**Severity**: Low  
**Component**: GitHub remote / repo identity  
**Status**: Resolved

## What Happened

Bootstrap tooling ASCII-mangled the Vietnamese folder name `CA-CÔNG-BẰNG` into `CA-C-NG-B-NG` when it created the GitHub repo. Every link in README, docs, and plan files pointed at a broken, unreadable slug.

## The Brutal Truth

This should have been caught before the first push. The repo name is the first thing anyone sees — shipping with garbled characters is embarrassing and makes every copy-pasted URL wrong.

## Actions Taken

- `gh repo rename CA-CONG-BANG` on `KanTrun/CA-C-NG-B-NG`
- Updated `README.md`, `docs/team.md`, `plan.md`, brainstorm report (4 files) — PR [#4](https://github.com/KanTrun/CA-CONG-BANG/pull/4)
- Cherry-picked rename commit onto `feat/api-sprint1` so PR [#3](https://github.com/KanTrun/CA-CONG-BANG/pull/3) won't reintroduce the old name
- Updated local `origin` remote URL; old GitHub URL auto-redirects

## Lesson

When the local folder name contains non-ASCII characters, always set `--name` explicitly during `gh repo create` rather than letting the CLI derive the slug. Add this to the bootstrap checklist.
