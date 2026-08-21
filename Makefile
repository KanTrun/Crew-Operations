.PHONY: setup contracts dev test test-unit lint demo demo-local demo-reset seed bench eval

setup:
	python -m pip install -e ./packages/contracts -e ./packages/solver -e ./packages/agents -e ./apps/api pytest httpx ruff pyyaml
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
	@echo "solver bench stub — hard checkers live in packages/solver"

eval:
	CA_AGENT_MODE=replay python -c "from ca_agents import AgentRuntime; print(AgentRuntime().run_replay('ag_tkb','0.1.0',{'x':1})['mode'])"
