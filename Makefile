.PHONY: setup contracts dev test test-unit lint demo demo-local demo-reset seed bench eval ab replay budget \
	docker-up docker-down docker-logs docker-smoke docker-ps

setup:
	python -m pip install -e ./packages/contracts -e ./packages/solver -e ./packages/agents -e ./packages/gates -e ./packages/opsengine -e ./packages/playbook -e ./apps/api pytest httpx ruff pyyaml
	cd apps/web && npm install

contracts:
	python scripts/export_contracts.py

dev:
	docker compose -f infra/docker/compose.yml up --build

demo-local:
	python scripts/demo_api.py

demo: demo-local

demo-reset:
	docker compose -f infra/docker/compose.yml down -v
	docker compose -f infra/docker/compose.yml up --build -d

test:
	CA_AGENT_MODE=replay python -m pytest -q

test-unit:
	CA_AGENT_MODE=replay python -m pytest -q

lint:
	ruff check apps/api/src packages scripts
	cd apps/web && npm run lint

seed:
	python scripts/generate_fixture_data.py

bench:
	python -m pip install -e ./packages/solver -e ./packages/playbook -q
	python scripts/solve_tuan.py
	python scripts/verify_hard.py

eval:
	CA_AGENT_MODE=replay python scripts/eval_ag_tkb.py
	CA_AGENT_MODE=replay python scripts/eval_ag_msg.py
	CA_AGENT_MODE=replay python -c "from fastapi.testclient import TestClient; from ca_api.interfaces.http.main import app; c=TestClient(app); t=c.post('/api/v1/auth/login', json={'username':'lan','password':'nhipquan'}).json()['token']; r=c.get('/api/v1/sop/golden', headers={'Authorization': f'Bearer {t}'}).json(); print('SOP', r['n'], r['moi_cau_co_nguon_hoac_chua_co'], r['co_cau_chua_co']); assert r['n']==20 and r['moi_cau_co_nguon_hoac_chua_co'] and r['co_cau_chua_co']"

ab:
	python scripts/ab_report.py

replay:
	@test -n "$(PHIEN)" || (echo "usage: make replay PHIEN=<idempotency-key>" && exit 1)
	CA_AGENT_MODE=replay python scripts/replay_orc.py "$(PHIEN)"

budget:
	@echo "budget stub — xem THIRD_PARTY.md; dùng OpenRouter dashboard khi bật live LLM"

# ── Docker toàn tuyến: postgres · redis · api · worker · web ──────────────────

docker-up:
	docker compose -f infra/docker/compose.yml up -d --build
	docker compose -f infra/docker/compose.yml ps

docker-down:
	docker compose -f infra/docker/compose.yml down

docker-ps:
	docker compose -f infra/docker/compose.yml ps

docker-logs:
	docker compose -f infra/docker/compose.yml logs -f --tail=100

docker-smoke:
	docker compose -f infra/docker/compose.yml exec -T api python /app/scripts/smoke_docker.py
