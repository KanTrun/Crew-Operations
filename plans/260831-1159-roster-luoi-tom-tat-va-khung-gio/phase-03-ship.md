---
phase: 3
title: "Ship: test, docker, git"
status: completed
priority: P2
effort: "2h"
dependencies: [1, 2]
---

# Phase 3: Ship

## Overview

Verify build, API tests, docker web image, git push.

## Success Criteria

- [ ] `npm --prefix apps/web run build`
- [ ] `pytest apps/api/tests/unit/test_lich_tuan_khung.py`
- [ ] `docker compose -f infra/docker/compose.yml build web`
- [ ] git commit + push origin main
