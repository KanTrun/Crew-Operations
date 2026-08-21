.PHONY: setup contracts dev test test-unit lint demo demo-reset seed bench eval

setup:
	python -m pip install -e ./packages/contracts -e ./apps/api
	cd apps/web && npm install

contracts:
	@echo "contracts: pydantic models in packages/contracts (OpenAPI export comes Sprint 1)"

dev:
	docker compose -f infra/docker/compose.yml up --build

test:
	CA_AGENT_MODE=replay python -m pytest -q

test-unit:
	CA_AGENT_MODE=replay python -m pytest -q -m "not integration"

lint:
	ruff check apps packages || true
	cd apps/web && npm run lint

demo: dev

demo-reset:
	docker compose -f infra/docker/compose.yml down -v
	docker compose -f infra/docker/compose.yml up --build -d

seed:
	python scripts/seed_stub.py

bench:
	@echo "solver bench stub"

eval:
	@echo "agent eval stub — CA_AGENT_MODE=replay"
